from typing import List, Dict, TypedDict
import random
import os
import time
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

class GameEntity(Enum):
    EMPTY = " "
    PLAYER = "P"
    CENTIPEDE = "O"
    MUSHROOM = "M"
    BULLET = "·"

class Direction(Enum):
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    DOWN = (0, 1)

@dataclass
class Position:
    x: int
    y: int

    def move(self, direction: Direction) -> 'Position':
        dx, dy = direction.value
        return Position(self.x + dx, self.y + dy)

    def distance_to(self, other: 'Position') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

class GameState(TypedDict):
    board: List[List[str]]
    score: int
    player_pos: Position
    centipede_segments: List[Position]
    mushrooms: List[Position]
    bullets: List[Position]
    game_over: bool
    direction: Direction

class Agent(ABC):
    @abstractmethod
    def make_decision(self, state: GameState) -> GameState:
        pass

class ShooterAgent(Agent):
    def __init__(self, strategy: str = "predictive"):
        self.strategy = strategy
        
    def predict_centipede_position(self, state: GameState) -> Position:
        if not state['centipede_segments']:
            return state['player_pos']
        
        head = state['centipede_segments'][0]
        direction = state['direction']
        
        # Predict where the head will be in the next move
        if direction == Direction.RIGHT and head.x < len(state['board'][0]) - 1:
            return Position(head.x + 1, head.y)
        elif direction == Direction.LEFT and head.x > 0:
            return Position(head.x - 1, head.y)
        else:
            # If centipede will change direction, predict it will move down
            return Position(head.x, head.y + 1)

    def make_decision(self, state: GameState) -> GameState:
        if not state['centipede_segments']:
            return state

        if self.strategy == "predictive":
            target = self.predict_centipede_position(state)
        else:
            target = state['centipede_segments'][0]  # Target the current head position

        # Move towards the x-position of the target
        if state['player_pos'].x < target.x:
            state = move_player(state, Direction.RIGHT)
        elif state['player_pos'].x > target.x:
            state = move_player(state, Direction.LEFT)
        
        # Shoot if aligned with target or close enough
        if abs(state['player_pos'].x - target.x) <= 1:
            state = shoot(state)
        
        return state

class CentipedeAgent(Agent):
    def __init__(self, strategy: str = "evasive"):
        self.strategy = strategy
        self.direction_change_cooldown = 0

    def make_decision(self, state: GameState) -> GameState:
        if not state['centipede_segments']:
            return state

        head = state['centipede_segments'][0]
        current_direction = state['direction']
        
        # Check for bullets nearby
        for bullet in state['bullets']:
            if abs(bullet.x - head.x) <= 1 and bullet.y < head.y:
                # Try to evade bullets
                if self.direction_change_cooldown <= 0:
                    if current_direction == Direction.RIGHT:
                        state['direction'] = Direction.LEFT
                    else:
                        state['direction'] = Direction.RIGHT
                    self.direction_change_cooldown = 3
        
        self.direction_change_cooldown = max(0, self.direction_change_cooldown - 1)
        
        # Occasionally change direction randomly for unpredictability
        if self.strategy == "evasive" and random.random() < 0.1 and self.direction_change_cooldown <= 0:
            state['direction'] = Direction.LEFT if current_direction == Direction.RIGHT else Direction.RIGHT
            self.direction_change_cooldown = 3
            
        return state

def initialize_board(width: int = 20, height: int = 20) -> List[List[str]]:
    return [[GameEntity.EMPTY.value for _ in range(width)] for _ in range(height)]

def initialize_game(width: int = 20, height: int = 20) -> GameState:
    board = initialize_board(width, height)
    
    # Place player at bottom center
    player_pos = Position(width // 2, height - 1)
    board[player_pos.y][player_pos.x] = GameEntity.PLAYER.value
    
    # Create centipede at top
    centipede_segments = [Position(i, 0) for i in range(8)]
    for segment in centipede_segments:
        board[segment.y][segment.x] = GameEntity.CENTIPEDE.value
    
    # Place random mushrooms
    mushrooms = []
    for _ in range(20):
        x = random.randint(0, width - 1)
        y = random.randint(2, height - 3)
        pos = Position(x, y)
        mushrooms.append(pos)
        board[pos.y][pos.x] = GameEntity.MUSHROOM.value
    
    return GameState(
        board=board,
        score=0,
        player_pos=player_pos,
        centipede_segments=centipede_segments,
        mushrooms=mushrooms,
        bullets=[],
        game_over=False,
        direction=Direction.RIGHT
    )

def print_board(board: List[List[str]], score: int):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"Score: {score}")
    print("+" + "-" * len(board[0]) + "+")
    for row in board:
        print("|" + "".join(row) + "|")
    print("+" + "-" * len(board[0]) + "+")

def update_game_state(state: GameState) -> GameState:
    board = state['board']
    width = len(board[0])
    height = len(board)
    
    # Clear current positions
    for y in range(height):
        for x in range(width):
            board[y][x] = GameEntity.EMPTY.value
    
    # Update bullets
    new_bullets = []
    for bullet in state['bullets']:
        new_pos = Position(bullet.x, bullet.y - 1)
        if new_pos.y >= 0:
            # Check for collisions
            hit_centipede = False
            for i, segment in enumerate(state['centipede_segments']):
                if new_pos.x == segment.x and new_pos.y == segment.y:
                    state['score'] += 10
                    # Convert hit segment to mushroom
                    state['mushrooms'].append(Position(segment.x, segment.y))
                    del state['centipede_segments'][i]
                    hit_centipede = True
                    break
            
            if not hit_centipede:
                new_bullets.append(new_pos)
    state['bullets'] = new_bullets
    
    # Update centipede movement
    if state['centipede_segments']:
        head = state['centipede_segments'][0]
        new_direction = state['direction']
        
        # Check if centipede needs to move down and change direction
        if (head.x == 0 and new_direction == Direction.LEFT) or \
           (head.x == width - 1 and new_direction == Direction.RIGHT):
            new_direction = Direction.LEFT if new_direction == Direction.RIGHT else Direction.RIGHT
            # Move all segments down
            state['centipede_segments'] = [Position(s.x, s.y + 1) for s in state['centipede_segments']]
        
        # Move centipede
        new_segments = []
        for i, segment in enumerate(state['centipede_segments']):
            if i == 0:
                new_pos = segment.move(new_direction)
            else:
                new_pos = state['centipede_segments'][i-1]
            new_segments.append(new_pos)
        
        state['centipede_segments'] = new_segments
        state['direction'] = new_direction
    
    # Update board with current state
    # Place mushrooms
    for mushroom in state['mushrooms']:
        board[mushroom.y][mushroom.x] = GameEntity.MUSHROOM.value
    
    # Place bullets
    for bullet in state['bullets']:
        board[bullet.y][bullet.x] = GameEntity.BULLET.value
    
    # Place centipede
    for segment in state['centipede_segments']:
        board[segment.y][segment.x] = GameEntity.CENTIPEDE.value
    
    # Place player
    board[state['player_pos'].y][state['player_pos'].x] = GameEntity.PLAYER.value
    
    # Check game over conditions
    for segment in state['centipede_segments']:
        if segment.y >= height - 1:
            state['game_over'] = True
            
    if not state['centipede_segments']:
        state['game_over'] = True
    
    return state

def move_player(state: GameState, direction: Direction) -> GameState:
    new_pos = state['player_pos'].move(direction)
    if 0 <= new_pos.x < len(state['board'][0]) and \
       0 <= new_pos.y < len(state['board']):
        state['player_pos'] = new_pos
    return state

def shoot(state: GameState) -> GameState:
    bullet_pos = Position(state['player_pos'].x, state['player_pos'].y - 1)
    state['bullets'].append(bullet_pos)
    return state

def play_game_with_agents(shooter_agent: ShooterAgent, centipede_agent: CentipedeAgent, delay: float = 0.1):
    state = initialize_game()
    print_board(state['board'], state['score'])
    
    while not state['game_over']:
        # Let agents make their decisions
        state = shooter_agent.make_decision(state)
        state = centipede_agent.make_decision(state)
        
        # Update and display game state
        state = update_game_state(state)
        print_board(state['board'], state['score'])
        
        # Add delay for visualization
        time.sleep(delay)
    
    print(f"Game Over! Final Score: {state['score']}")
    if not state['centipede_segments']:
        print("Shooter wins!")
    else:
        print("Centipede wins!")

if __name__ == "__main__":
    # Create agents with different strategies
    shooter = ShooterAgent(strategy="predictive")
    centipede = CentipedeAgent(strategy="evasive")
    
    # Start the game with agents
    play_game_with_agents(shooter, centipede, delay=0.2)