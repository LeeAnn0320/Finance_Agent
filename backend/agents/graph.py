
from typing import List,Literal,Dict,Any,Optional,TypedDict

from langgraph.graph import StateGraph,END
from langgraph.checkpoint.memory import MemorySaver
from agents.nodes import RouterNode,PlannerNode,ExecuteNode,ReflectionNode,CriticNode
from datetime import datetime

class FinanceAnalystState(TypedDict):
    messages:List[Dict[str,str]]
    conversation_history:str
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


def create_finance_analyst_graph():
    """
    创建金融分析师工作流图
    1.路由节点
    2.计划节点
    3.执行节点
    4.反思节点
    5.集成（生成最终答案）节点
    """
    router=RouterNode()
    planner=PlannerNode()
    executor=ExecuteNode()
    reflector=ReflectionNode()
    critic=CriticNode()

    workflow=StateGraph(FinanceAnalystState)

    #添加节点
    workflow.add_node("router", router)
    workflow.add_node("planner", planner)
    workflow.add_node("executor", executor)
    workflow.add_node("reflector", reflector)
    workflow.add_node("critic", critic)

    #设置入口
    workflow.set_entry_point("router")

    #连接边
    workflow.add_edge("router","planner")
    workflow.add_edge("planner","executor")

    #执行节点的条件边
    def should_continue_execution(state:FinanceAnalystState)->Literal["executor","reflector"]:
        if state.get("should_continue",False):
            return "executor"
        return "reflector"
    workflow.add_conditional_edges(
        "executor",should_continue_execution,{
            "executor":"executor",
            "reflector":"reflector"
        }
    )

    #反思节点的条件边
    def should_reflect_again(state:FinanceAnalystState)->Literal["planner","critic"]:
        if state.get("should_continue",False) and state.get("iteration",0)<state.get("max_iterations",3):
            return "planner"
        return "critic"
    workflow.add_conditional_edges(
        "reflector",should_reflect_again,{
            "critic":"critic",
            "planner":"planner"
        }
    )
    workflow.add_edge("critic",END)
    memory=MemorySaver()
    app=workflow.compile(checkpointer=memory)

    return app


class FinanceAnalystAgent:
    def __init__(self):
        self.graph = create_finance_analyst_graph()
        self.session_histories: Dict[str, List[Dict[str, str]]] = {}

    def _get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.session_histories.setdefault(session_id, [])

    def _format_history(self, history: List[Dict[str, str]], limit: int = 8) -> str:
        if not history:
            return "无历史对话"

        recent_messages = history[-limit:]
        role_names = {
            "user": "用户",
            "assistant": "助手"
        }
        return "\n".join(
            f"{role_names.get(message.get('role'), message.get('role', '未知'))}: {message.get('content', '')}"
            for message in recent_messages
        )

    def _build_initial_state(self, query: str, max_iterations: int, session_id: str) -> Dict[str, Any]:
        history = self._get_history(session_id)
        return {
            "messages": history + [{"role": "user", "content": query}],
            "conversation_history": self._format_history(history),
            "query": query,
            "intent": "",
            "plan": [],
            "current_step": 0,
            "tool_calls": [],
            "tool_results": [],
            "reasoning_steps": [],
            "reflections": [],
            "should_continue": True,
            "iteration": 0,
            "max_iterations": max_iterations,
            "final_answer": "",
            "error": None
        }

    def _save_turn(self, session_id: str, query: str, answer: str):
        history = self._get_history(session_id)
        history.extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": answer}
        ])
        self.session_histories[session_id] = history[-20:]

    def analyze(self, query: str, max_iterations: int = 3, session_id: str = "default") -> Dict[str, Any]:
        initial_state = self._build_initial_state(query, max_iterations, session_id)
        config = {"configurable": {"thread_id": session_id}}
        try:
            result = self.graph.invoke(input=initial_state, config=config)
            answer = result.get("final_answer", "")
            self._save_turn(session_id, query, answer)
            return {
                "success": True,
                "query": query,
                "intent": result.get("intent", ""),
                "answer": answer,
                "reasoning_steps": result.get("reasoning_steps", []),
                "reflections": result.get("reflections", []),
                "tool_results": result.get("tool_results", []),
                "iterations": result.get("iteration", 0)
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "answer": f"分析过程中出现错误: {str(e)}"
            }

    def stream_analyze(self, query: str, max_iterations: int = 3, session_id: str = "default"):
        """
        流式执行金融分析

        Args:
            query: 用户查询
            max_iterations: 最大迭代次数
            session_id: 会话ID，用于区分不同对话历史

        Yields:
            每个步骤的状态更新
        """
        initial_state = self._build_initial_state(query, max_iterations, session_id)

        config = {"configurable": {"thread_id": session_id}}

        try:
            final_answer = ""
            for event in self.graph.stream(initial_state, config):
                for node_name, state in event.items():
                    if state.get("final_answer"):
                        final_answer = state["final_answer"]
                    yield {
                        "node": node_name,
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    }
            self._save_turn(session_id, query, final_answer)
        except Exception as e:
            yield {
                "node": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

def analyze_query(query:str,max_iterations:int=3)->Dict[str,Any]:
    agent=FinanceAnalystAgent()    
    return agent.analyze(query=query,max_iterations=max_iterations)

if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("金融研报自动化分析师 - 测试")
    print("=" * 60)
    
    # 初始化数据库
    from database.init_db import init_database
    init_database()
    
    # 测试查询
    test_queries = [
        # "市值最大的5只银行股是哪些？",
        "分析一下贵州茅台的财务状况",
        # "最近新能源行业有什么新闻？"
    ]
    
    agent = FinanceAnalystAgent()
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print("=" * 60)
        
        result = agent.analyze(query)
        
        print(f"\n意图: {result.get('intent', 'N/A')}")
        print(f"\n推理过程:")
        for step in result.get("reasoning_steps", []):
            print(f"  {step}")
        
        print(f"\n最终答案:")
        print(result.get("answer", "无答案"))
        
        print(f"\n迭代次数: {result.get('iterations', 0)}")
