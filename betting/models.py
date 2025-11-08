from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Team:
    """Represents a football team"""
    id: int
    name: str
    logo: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'Team':
        """Create a Team object from API data"""
        if not data:
            return None
            
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            logo=data.get('logo'),
            country=data.get('country', {}).get('name') if 'country' in data else None,
            founded=data.get('founded')
        )

@dataclass
class Match:
    """Represents a football match"""
    id: int
    home_team: Team
    away_team: Team
    date: datetime
    league_id: int
    league_name: str
    country: str
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'Match':
        """Create a Match object from API data"""
        if not data or 'teams' not in data or 'fixture' not in data:
            return None
            
        teams = data['teams']
        fixture = data['fixture']
        league = data.get('league', {})
        goals = data.get('goals', {})
        
        try:
            match_date = datetime.fromisoformat(fixture.get('date', '').replace('Z', '+00:00'))
        except (ValueError, TypeError):
            match_date = None
        
        return cls(
            id=fixture.get('id'),
            home_team=Team.from_api(teams.get('home')),
            away_team=Team.from_api(teams.get('away')),
            date=match_date,
            league_id=league.get('id'),
            league_name=league.get('name'),
            country=league.get('country'),
            status=fixture.get('status', {}).get('short'),
            home_score=goals.get('home'),
            away_score=goals.get('away')
        )

@dataclass
class TeamStats:
    """Represents team statistics"""
    team_id: int
    team_name: str
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0
    failed_to_score: int = 0
    form: str = ""
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    
    def calculate_averages(self):
        """Calculate average statistics"""
        if self.matches_played > 0:
            self.avg_goals_scored = self.goals_scored / self.matches_played
            self.avg_goals_conceded = self.goals_conceded / self.matches_played

@dataclass
class HeadToHeadStats:
    """Represents head-to-head statistics between two teams"""
    team1_id: int = 0
    team2_id: int = 0
    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    goals_for: int = 0
    goals_against: int = 0
    avg_goals: float = 0.0
    matches: List[Match] = field(default_factory=list)
    
    def __post_init__(self):
        # For backward compatibility
        if hasattr(self, 'team1_wins') and not hasattr(self, 'home_wins'):
            self.home_wins = self.team1_wins
        if hasattr(self, 'team2_wins') and not hasattr(self, 'away_wins'):
            self.away_wins = self.team2_wins

@dataclass
class Prediction:
    """Represents a match prediction"""
    match: Match
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_home_score: float
    predicted_away_score: float
    confidence: float
    over_under_predictions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    btts_prediction: Dict[str, Any] = field(default_factory=dict)
    first_half_prediction: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def predicted_outcome(self) -> str:
        """Get the predicted outcome based on probabilities"""
        probs = {
            'home': self.home_win_probability,
            'draw': self.draw_probability,
            'away': self.away_win_probability
        }
        return max(probs, key=probs.get)
    
    @property
    def predicted_score(self) -> str:
        """Get the predicted score as a string"""
        return f"{int(round(self.predicted_home_score))}-{int(round(self.predicted_away_score))}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary for JSON serialization"""
        return {
            'match': {
                'id': self.match.id,
                'home_team': self.match.home_team.name,
                'away_team': self.match.away_team.name,
                'date': self.match.date.isoformat() if self.match.date else None,
                'league': self.match.league_name,
                'country': self.match.country
            },
            'probabilities': {
                'home': round(self.home_win_probability * 100, 1),
                'draw': round(self.draw_probability * 100, 1),
                'away': round(self.away_win_probability * 100, 1)
            },
            'prediction': self.predicted_outcome,
            'score': {
                'home': int(round(self.predicted_home_score)),
                'away': int(round(self.predicted_away_score)),
                'display': self.predicted_score
            },
            'confidence': round(self.confidence * 100, 1),
            'over_under': self.over_under_predictions,
            'btts': self.btts_prediction,
            'first_half': self.first_half_prediction
        }
