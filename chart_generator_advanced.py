import functools
import json
import operator
import os
from typing import Annotated, Sequence, Optional

from dotenv import load_dotenv
from langchain_core.utils.function_calling import convert_to_openai_function

load_dotenv(".env")

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import BaseMessage, FunctionMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.graph import MermaidDrawMethod, CurveStyle, NodeColors
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from typing_extensions import TypedDict


class DatabaseConfig:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db = None

    def configure(self):
        SQLALCHEMY_DATABASE_URL = f"{self.db_path}"
        self.db = SQLDatabase.from_uri(SQLALCHEMY_DATABASE_URL)

    def get_db(self):
        return self.db


class AgentManager:
    """
    This class is responsible for defining the tools and agents that will be used in the workflow.
    """

    def __init__(self, llm, db, tables_names, query):
        self.llm = llm
        self.db = db
        self.tables_names = tables_names
        self.query = query
        self.research_agent_sql = None
        self.chart_agent = None
        self.tool_executor = None

    def get_db_schema(self):

        schema_str = ""
        for table_name in self.tables_names:
            columns = self.db._inspector.get_columns(table_name)
            schema_str += f"Schema for table '{table_name}':\n"
            for column in columns:
                schema_str += f"  - {column['name']} ({column['type']})\n"
            schema_str += "\n"

        return schema_str

    def create_agent(self, llm, tools, system_message: str):
        functions = [convert_to_openai_function(t) for t in
                     tools]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " If you are unable to fully answer, that's OK, another assistant with different tools "
                    " will help where you left off. Execute what you can to make progress."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    " Once you have retrieved the data, pass the control to the python_repl tool to analyze it."
                    " Prefix your response with FINAL ANSWER once you have generated the chart."
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        return prompt | llm.bind_functions(functions)

    def create_agents(self):

        schema = self.get_db_schema()

        prompt_sql = f"""\
        You are an expert at SQL lite. You have access to a SQL lite database \
        with the following tables:
        
        {schema}

        
        Given a user question related to the data in the database, \
        first get the relevant data from the table as a DataFrame using the create_df_from_sql tool. 
                
        """

        prompt_sql_with_advice = f"""\ 
        {prompt_sql}
        This is what the user asked: "{self.query}"
        """
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        tools_sql = toolkit.get_tools()[0]

        if self.query:
            self.research_agent_sql = self.create_agent(self.llm, [tools_sql], system_message=prompt_sql_with_advice)
        else:

            self.research_agent_sql = self.create_agent(self.llm, [tools_sql], system_message=prompt_sql)

        repl = PythonREPL()

        @tool
        def python_repl(code: Annotated[str, "The python code to execute to generate your chart."]):
            """Use this to execute python code. If you want to see the output of a value,
            you should print it out with `print(...)`. This is visible to the user."""
            try:
                result = repl.run(code)
            except BaseException as e:
                return f"Failed to execute. Error: {repr(e)}"
            return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"

        name_directory = ""

        for name in self.tables_names:
            name_directory += name + "_"

        ## se la cartella 'plots/'"+self.table_name+"/ non esiste la crea
        if not os.path.exists('plots/' + name_directory):
            os.makedirs('plots/' + name_directory)

        self.chart_agent = self.create_agent(
            self.llm,
            [python_repl],
            system_message="Any charts you display will be visible by the user. "
                           "Don't ask the user what type of chart they want, just make a decision and display it. "
                           "Save the chart as an SVG file in the 'plots/" + name_directory + "/' directory, give an appropriate name to the chart.",
        )

        self.tool_executor = ToolExecutor([tools_sql, python_repl])


class WorkflowManager:

    """
     The class is resposnable of creating the functions that will be the nodes of the graph, connect them with edges.
     The functions use the agents to perform actions.
     The class is even responsable of executing the workflow with the method execute_workflow.
     """


    def __init__(self, research_agent_sql, chart_agent, tool_executor):
        self.research_agent_sql = research_agent_sql
        self.chart_agent = chart_agent
        self.tool_executor = tool_executor

    def create_workflow(self):

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], operator.add]
            sender: str

        def agent_node(state, agent, name):
            result = agent.invoke(state)
            print(result)

            if not isinstance(result, FunctionMessage):
                result = HumanMessage(**result.dict(exclude={"type", "name"}), name=name)
            return {"messages": [result], "sender": name}

        def tool_node(state):
            messages = state["messages"]
            last_message = messages[-1]
            arguments = last_message.additional_kwargs["function_call"]["arguments"]
            ## OpenAI returns sometimes the string as JSON-like string (e.g., '{"my_value":"value"}')
            ## and sometimes it is a plain string (e.g., 'value').
            if arguments.startswith('{') and arguments.endswith('}'):
                tool_input = json.loads(arguments)
            else:
                tool_input = {'code': arguments}
            if len(tool_input) == 1 and "__arg1" in tool_input:
                tool_input = next(iter(tool_input.values()))
            tool_name = last_message.additional_kwargs["function_call"]["name"]
            action = ToolInvocation(tool=tool_name, tool_input=tool_input)
            response = self.tool_executor.invoke(action)
            function_message = FunctionMessage(content=f"{tool_name} response: {str(response)}", name=action.tool)
            return {"messages": [function_message]}

        def router(state):
            messages = state["messages"]
            last_message = messages[-1]
            if "FINAL ANSWER" in last_message.content:
                return "end"
            if "function_call" in last_message.additional_kwargs:
                return "call_tool"
            return "continue"

        workflow = StateGraph(AgentState)
        workflow.add_node("SQLResearcher",
                          functools.partial(agent_node, agent=self.research_agent_sql, name="SQLResearcher"))
        workflow.add_node("Chart Generator",
                          functools.partial(agent_node, agent=self.chart_agent, name="Chart Generator"))
        workflow.add_node("call_tool", tool_node)

        workflow.add_conditional_edges(
            "SQLResearcher",
            router,
            {"continue": "Chart Generator", "call_tool": "call_tool", "end": END},
        )
        workflow.add_conditional_edges(
            "Chart Generator",
            router,
            {"call_tool": "call_tool", "end": END},
        )
        workflow.add_conditional_edges(
            "call_tool",
            lambda x: x["sender"],
            {"SQLResearcher": "SQLResearcher", "Chart Generator": END},
        )
        workflow.set_entry_point("SQLResearcher")

        return workflow

    def execute_workflow(self, initial_state, recursion_limit=150):
        graph = self.create_workflow().compile()

        graph.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeColors(start="#ffdfba", end="#baffc9", other="#fad7de"),
            wrap_label_n_words=9,
            output_file_path='graph.png',
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10
        )

        for state in graph.stream(initial_state, {"recursion_limit": recursion_limit}):
            print(state)
            print("----")


class Main:
    @staticmethod
    def run(tables_names: str, query: Optional[str] = None):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

        db_config = DatabaseConfig(db_path=f"sqlite:///{ROOT_DIR}/test.db")
        db_config.configure()

        llm = ChatOpenAI(model_name="gpt-4o")

        agent_manager = AgentManager(llm=llm, db=db_config.get_db(), tables_names=tables_names,
                                     query=query)
        agent_manager.create_agents()

        workflow_manager = WorkflowManager(
            research_agent_sql=agent_manager.research_agent_sql,
            chart_agent=agent_manager.chart_agent,
            tool_executor=agent_manager.tool_executor
        )

        initial_state = {
            "messages": [HumanMessage(content="Get me some usefull data")]
        }
        workflow_manager.execute_workflow(initial_state)


if __name__ == "__main__":
    Main.run(["users", "orders"], "Plot me the number of orders per user.")
