from typing import List, Dict, TypedDict
import openai
import anthropic
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END

# Load environment variables from .env file
load_dotenv()

# Set up your API keys from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')
anthropic.api_key = os.getenv('ANTHROPIC_API_KEY')

class ChessGameState(TypedDict):
    board: List[List[str]]
    current_turn: str
    game_over: bool
    winner: str

def initialize_board() -> List[List[str]]:
    return [
        ["r", "n", "b", "q", "k", "b", "n", "r"],
        ["p", "p", "p", "p", "p", "p", "p", "p"],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        ["P", "P", "P", "P", "P", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "B", "N", "R"]
    ]

def print_board(board: List[List[str]]):
    for row in board:
        print(" ".join(row))
    print()

class OpenAIAgent:
    def get_move(self, board: List[List[str]], current_turn: str) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a chess expert."},
                {"role": "user", "content": f"Given the current chess board:\n{self.format_board(board)}\nWhat is the best move for {current_turn}?"}
            ],
            max_tokens=50
        )
        return response.choices[0].message['content'].strip()

    def format_board(self, board: List[List[str]]) -> str:
        return "\n".join(" ".join(row) for row in board)

class AnthropicAgent:
    def get_move(self, board: List[List[str]], current_turn: str) -> str:
        # Simulate interaction with Anthropic's API
        return "e2e4"  # Placeholder move

def make_move(state: ChessGameState, player: str, agent) -> ChessGameState:
    move = agent.get_move(state['board'], state['current_turn'])
    print(f"{player} makes move: {move}")
    # Implement move execution logic here
    # For now, just toggle the turn
    state['current_turn'] = 'black' if state['current_turn'] == 'white' else 'white'
    return state

def player_white_node(state: ChessGameState) -> ChessGameState:
    openai_agent = OpenAIAgent()
    return make_move(state, "OpenAI", openai_agent)

def player_black_node(state: ChessGameState) -> ChessGameState:
    anthropic_agent = AnthropicAgent()
    return make_move(state, "Anthropic", anthropic_agent)

def play_chess_game():
    initial_state = ChessGameState(
        board=initialize_board(),
        current_turn='white',
        game_over=False,
        winner=""
    )

    workflow = StateGraph(ChessGameState)
    workflow.add_node("player_white", player_white_node)
    workflow.add_node("player_black", player_black_node)

    def route_step(state: ChessGameState) -> str:
        if state['game_over']:
            return END
        return "player_white" if state['current_turn'] == 'white' else "player_black"

    workflow.add_edge(START, "player_white")
    workflow.add_conditional_edges("player_white", route_step)
    workflow.add_conditional_edges("player_black", route_step)

    chain = workflow.compile()
    result = chain.invoke(initial_state)

    print("Game Over")
    print_board(result['board'])

def main():
    print("Starting a game of chess between OpenAI and Anthropic agents.")
    play_chess_game()

if __name__ == "__main__":
    main()
