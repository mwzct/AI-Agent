from langchain.tools import tool

@tool
def add(a: int, b: int) -> int:
    """add two numbers"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """multiply two number"""
    return a * b