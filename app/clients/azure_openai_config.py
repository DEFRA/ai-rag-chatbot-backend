from langchain_openai import AzureChatOpenAI

from app.config import config as configs


def azure_gpt4(temperature=0, streaming=True):
    try:
        gpt4_chat_azure = AzureChatOpenAI(
            azure_deployment=configs.AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=temperature,
            api_key=configs.AZURE_OPENAI_API_KEY,
            azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
            api_version=configs.AZURE_API_VERSION,
            streaming=streaming,
        )
        print("gpt4_chat_azure initialized successfully.")
        return gpt4_chat_azure
    except Exception as e:
        print(f"Error initializing gpt4_chat_azure: {e}")


def azure_gpt4o(temperature=0, streaming=True):
    try:
        gpt4o_chat_azure = AzureChatOpenAI(
            azure_deployment=configs.AZURE_OPENAI_DEPLOYMENT_NAME_4o,
            temperature=temperature,
            api_key=configs.AZURE_OPENAI_API_KEY,
            azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
            api_version=configs.AZURE_API_VERSION,
            streaming=streaming,
        )
        print("gpt4o_chat_azure initialized successfully.")
        return gpt4o_chat_azure
    except Exception as e:
        print(f"Error initializing gpt4o_chat_azure: {e}")
