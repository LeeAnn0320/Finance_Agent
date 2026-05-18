"""langgraph 节点实现"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict,Dict,List,Optional,Any
from services.llm import get_llm_service
import json
"""Agent状态 定义"""
class AgentState():
    messages:List[Dict[str,str]]
    query:str
    intent:str
    plan:List[str]
    current_step:int
    tool_calls:List[Dict[str,Any]]
    tool_results:List[Dict[str,Any]]
    reasoning_steps:List[str]
    reflections:List[str]
    final_answer:str
    should_continue:bool
    iteration:int
    max_iterations:int
    err:Optional[str]


'''路由节点函数：意图识别'''
class RouterNode():
    def __init__(self):
        self.llm=get_llm_service()
    def __call__(self, state:AgentState)->Dict[str,Any]:
        query=state["query"]
        prompt=f"""你是一个金融分析助手的路由器。分析用户的问题，判断应该使用哪种处理方式。

用户问题: {query}

可选的意图类型:
1. data_query - 数据查询：需要查询数据库获取股票、财务、行情等具体数据
2. analysis - 深度分析：需要综合多种数据进行分析，可能需要代码执行和可视化
3. research - 研报检索：需要检索研报内容或最新市场信息
4. general - 一般问答：简单的金融知识问答，不需要查询数据

请分析用户意图，返回JSON格式:
{{
    "intent": "意图类型",
    "reason": "判断理由",
    "suggested_tools": ["建议使用的工具列表"]
}}

只返回JSON，不要其他内容。"""
        response=self.llm.simple_chat(prompt=prompt)
        try:
            result=json.loads(response.strip())
            intent=result.get("intent","general")
            reason=result.get("reason","")
            suggested_tools=result.get("suggested_tools",[])
        except json.JSONEncoder:
            intent="general"
            resson="无法解析意图"
            suggested_tools=[]
        return {
            "intent":intent,
            "reason_steps":state.get("reasoning_steps",[])+[f"[路由]识别意图:{intent},理由:{reason}"]
        }
    

class PlannerNode:
    def __init__(self):
        self.llm=get_llm_service()
    def __call__(self,state:AgentState)->Dict[str,Any]:
        """指定计划"""
        query=state["query"]
        intent=state["intent"]

        if intent=="analysis":
            return 


        prompt=f"""你是一个金融分析任务规划器。根据用户问题和识别的意图，制定详细的执行计划。

用户问题: {query}
识别意图: {intent}

可用工具:
1. text2sql - 将自然语言转SQL查询数据库（股票信息、财务数据、行情、研报记录）
2. web_search - 搜索最新市场信息


请制定执行计划，返回JSON格式:
{{
    "plan": [
        {{"step": 1, "action": "动作描述", "tool": "工具名称", "params": {{"参数"}}}},
        ...
    ],
    "reasoning": "规划理由"
}}

只返回JSON，不要其他内容。"""
        response=self.llm.chat(prompt=prompt)
        try:
            result=json.loads(response.strip())
            plan=result.get("plan",[])
            reasoning=result.get("reasoning","")
        except json.JSONDecodeError:
            # 默认计划
            if intent == "data_query":
                plan = [{"step": 1, "action": "查询数据", "tool": "text2sql", "params": {"question": query}}]
            else:
                plan = [{"step": 1, "action": "直接回答", "tool": None, "params": {}}]
            reasoning = "使用默认计划"
        return {
            "plan":plan,
            "current_step":0,
            "reasoning_steps":state.get("reasoning_steps",[])+[f"[规划]指定了{len(plan)}步计划:{reasoning}"]
        }
    def _plan_with_code(query,state:AgentState)->Dict[str,any]:
        """分析类任务生成包含python代码的计划"""