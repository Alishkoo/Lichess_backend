import json
import httpx
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from celery import Task

from src.celery_app import celery_app
from src.config import settings
from src.games.models import Game
from src.auth.models import User


engine = create_engine(
    settings.database_url.replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(bind=engine)


class GameSyncTask(Task):
    def update_progress(self, current: int, total: int, message: str = ""):
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'message': message,
                'percent': int((current / total) * 100) if total > 0 else 0
            }
        )


@celery_app.task(bind=True, base=GameSyncTask, name='sync_user_games')
def sync_user_games(
    self,
    user_id: int,
    lichess_username: str,
    access_token: str,
    max_games: Optional[int] = None
) -> dict:
    session = SessionLocal()
    
    try:
        url = f"https://lichess.org/api/games/user/{lichess_username}"
        
        params = {
            "pgnInJson": "false",
            "clocks": "false",
            "evals": "false",
            "opening": "false",
        }
        
        if max_games:
            params["max"] = max_games
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/x-ndjson"
        }
        
        self.update_progress(0, 1, "Starting game synchronization...")
        
        games_to_insert = []
        games_processed = 0
        games_skipped = 0
        batch_size = 100
        total_games = 0
        
        with httpx.Client(timeout=300.0) as client:
            with client.stream("GET", url, params=params, headers=headers) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        game_data = json.loads(line)
                        total_games += 1
                        
                        game_id = game_data.get("id")
                        existing = session.execute(
                            select(Game).where(Game.id == game_id)
                        ).scalar_one_or_none()
                        
                        if existing:
                            games_skipped += 1
                            continue
                        
                        parsed_game = parse_game_data(
                            game_data=game_data,
                            user_id=user_id,
                            lichess_username=lichess_username
                        )
                        
                        if parsed_game:
                            games_to_insert.append(parsed_game)
                            games_processed += 1
                            
                            if len(games_to_insert) >= batch_size:
                                session.bulk_insert_mappings(Game, games_to_insert)
                                session.commit()
                                
                                self.update_progress(
                                    games_processed,
                                    total_games,
                                    f"Processed {games_processed} games..."
                                )
                                
                                games_to_insert = []
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error processing game: {e}")
                        continue
                
                if games_to_insert:
                    session.bulk_insert_mappings(Game, games_to_insert)
                    session.commit()
        
        result = {
            "status": "completed",
            "total_games": total_games,
            "processed": games_processed,
            "skipped": games_skipped,
            "message": f"Successfully synced {games_processed} new games"
        }
        
        self.update_progress(
            games_processed,
            total_games,
            f"Completed! Synced {games_processed} new games"
        )
        
        return result
    
    except httpx.HTTPStatusError as e:
        session.rollback()
        error_msg = f"Lichess API error: {e.response.status_code}"
        return {
            "status": "failed",
            "error": error_msg
        }
    
    except Exception as e:
        session.rollback()
        return {
            "status": "failed",
            "error": str(e)
        }
    
    finally:
        session.close()


def parse_game_data(game_data: dict, user_id: int, lichess_username: str) -> Optional[dict]:
    try:
        white_player = game_data.get("players", {}).get("white", {})
        black_player = game_data.get("players", {}).get("black", {})
        
        if white_player.get("user", {}).get("name", "").lower() == lichess_username.lower():
            user_color = "white"
            opponent = black_player
        elif black_player.get("user", {}).get("name", "").lower() == lichess_username.lower():
            user_color = "black"
            opponent = white_player
        else:
            return None
        
        winner = game_data.get("winner")
        if winner is None:
            result = "draw"
        elif winner == user_color:
            result = "win"
        else:
            result = "loss"
        
        game_id = game_data.get("id")
        created_at = datetime.fromtimestamp(game_data.get("createdAt", 0) / 1000)
        perf_type = game_data.get("perf")
        
        clock = game_data.get("clock", {})
        time_control = None
        if clock:
            initial = clock.get("initial", 0) // 60
            increment = clock.get("increment", 0)
            time_control = f"{initial}+{increment}"
        elif game_data.get("daysPerTurn"):
            time_control = f"{game_data['daysPerTurn']} days/move"
        
        opponent_user = opponent.get("user", {})
        opponent_name = opponent_user.get("name", "Anonymous")
        opponent_rating = opponent.get("rating")
        
        status = game_data.get("status")
        termination = map_termination(status)
        
        game_url = f"https://lichess.org/{game_id}"
        
        return {
            "id": game_id,
            "user_id": user_id,
            "created_at": created_at,
            "perf_type": perf_type,
            "time_control": time_control,
            "opponent_name": opponent_name,
            "opponent_rating": opponent_rating,
            "user_color": user_color,
            "result": result,
            "termination": termination,
            "url": game_url,
            "imported_at": datetime.utcnow()
        }
    
    except Exception as e:
        print(f"Error parsing game data: {e}")
        return None


def map_termination(status: str) -> str:
    status_map = {
        "mate": "checkmate",
        "resign": "resignation",
        "outoftime": "time",
        "timeout": "timeout",
        "draw": "draw",
        "stalemate": "stalemate",
        "cheat": "cheat",
        "noStart": "abandoned",
        "unknownFinish": "unknown",
        "variantEnd": "variant_end"
    }
    
    return status_map.get(status, "normal")
