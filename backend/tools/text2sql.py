import os 
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.llm import get_llm_service
from database.init_db import get_table_schema,get_db_session
import re
import json
from typing import Dict,Any
from sqlalchemy import text
class Text2SQLTool:
    """Text2SQL工具类  这段描述是有意义的，AI agent可以看的"""
    
    name = "text2sql"
    description = """将自然语言问题转换为SQL查询并执行。适用于：
    - 查询股票基本信息（市值、行业、PE/PB等）
    - 查询财务数据（营收、利润、ROE等）
    - 查询行情数据（价格、涨跌幅、成交量等）
    - 查询研报信息（评级、目标价、分析师观点等）
    - 进行数据筛选和排序（如：市值前10、ROE大于15%等）"""

    def __init__(self):
        self.llm=get_llm_service()
        self.schema=get_table_schema()
    def _generate_sql(self,question:str)->str:
        """生成SQL语句的提示词"""
        prompt=f"""
        你是一个专业的SQL生成器。根据用户的自然语言问题，生成对应的SQLite查询语句。
        数据库结构：
        {self.schema}
        用户问题：
        {question}
        要求:
        1. 只返回SQL语句，不要有任何解释
        2. 使用标准SQLite语法
        3. 表名和字段名要准确
        4. 如果需要关联查询，使用JOIN
        5. 适当使用ORDER BY和LIMIT来优化结果
        6. 股票代码是字符串类型，需要用引号
        7. 日期格式为 'YYYY-MM-DD'
        SQL语句:
        """
        
        response=self.llm.simple_chat(prompt=prompt)

        # 从 LLM 回复中提取 SQL
        sql = self._extract_sql(response)
        return sql

    def _extract_sql(self, text: str) -> str:
        """
        从 LLM 回复中提取 SQL 语句

        Args:
            text: LLM 返回的原始文本

        Returns:
            提取出的 SQL 语句
        """
        # 优先匹配 markdown 代码块内的 SQL
        code_block_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            return code_block_match.group(1).strip()

        # 其次匹配 markdown 代码块（无语言标识）
        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # 匹配以 SELECT/INSERT/UPDATE/DELETE/WITH 开头的 SQL 语句
        sql_match = re.search(
            r'(SELECT|INSERT|UPDATE|DELETE|WITH\s+\w+).*?(?:;|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if sql_match:
            return sql_match.group(0).strip().rstrip(';')

        # 最后兜底：直接返回清洗后的原文
        return text.strip().strip(';').strip('`')
    
    def _execute_sql(self,sql:str)->Dict[str,any]:
        session =get_db_session()
        '''
          SQL 查询结果像一个 Excel 表格：

           stock_code | stock_name | industry
          ------------+------------+---------
   row 0:  '601398'   | '工商银行' | '银行'
   row 1:  '601288'   | '农业银行' | '银行'

  columns = result.keys()  → ['stock_code', 'stock_name', 'industry']
  rows    = result.fetchall() → [('601398', '工商银行', '银行'), ('601288', '农业银行', '银行')]


    data = [
      {
          'stock_code': '601398',
          'stock_name': '工商银行',
          'industry': '银行'
      },
      {
          'stock_code': '601288',
          'stock_name': '农业银行',
          'industry': '银行'
      }
  ]
        '''
        try:
            # SQLAlchemy2.0需要用text()包装原始sql
            result=session.execute(text(sql))
            rows=result.fetchall()#获取所有行 是一个列表，每行是一个元组
            columns= result.keys()#获取列名
            data =[dict(zip(columns,row)) for row in rows]#元组转字典
            return {
                "success": True,
                "sql": sql,
                "data": data,
                "row_count": len(data)
            }
        except Exception as e:
            return {
                "success": False,
                "sql": sql,
                "error": str(e)
            }
        finally:
            session.close()

    def _format_result(self,question:str,result:Dict[str,Any])->str:
        if not result["success"]:
            return f"查询失败:{result['error']}\n 生成的SQL:{result['sql']}"
        if result["row_count"]==0:
            return f"查询成果，但没有找到符合条件的数据。\n 执行的SQL:{result['sql']}"
        # 让LLM生成自然语言回复
        prompt = f"""根据SQL查询结果，用中文自然语言回答用户的问题。

        用户问题: {question}

        执行的SQL: {result['sql']}

        查询结果（共{result['row_count']}条）:
        {json.dumps(result['data'][:20], ensure_ascii=False, indent=2)}

        请用清晰、专业的语言总结查询结果，如果数据较多，突出重点信息。"""
        response=self.llm.simple_chat(prompt=prompt)
        return response
    
    def run(self,question:str,return_raw:bool=False)->Dict[str,Any]:
        #生成sql
        sql=self._generate_sql(question=question)
        #执行sql
        result=self._execute_sql(sql=sql)

        if return_raw:
            return result
        answer =self._format_result(question=question,result=result)
        return {
            "question": question,
            "sql": sql,
            "raw_data": result.get("data", []),
            "row_count": result.get("row_count", 0),
            "answer": answer,
            "success": result["success"]
        }
    
# 工具函数定义（用于LangGraph）
TEXT2SQL_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "text2sql",
        "description": "将自然语言问题转换为SQL查询并执行。适用于查询股票信息、财务数据、行情数据、研报信息等。",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "需要查询的自然语言问题，如'市值最大的5只银行股'、'ROE大于15%的股票有哪些'"
                }
            },
            "required": ["question"]
        }
    }
}

if __name__ == "__main__":
    # 测试
    tool = Text2SQLTool()
    
    # 初始化数据库
    from database.init_db import init_database
    init_database()
    
    questions = [
        "市值最大的5只股票是哪些？",
        "银行板块有哪些股票？",
        "ROE大于15%的股票有哪些？",
    ]
    
    for q in questions:
        print(f"\n问题: {q}")
        result = tool.run(q)
        print(f"SQL: {result['sql']}")
        print(f"回答: {result['answer']}")