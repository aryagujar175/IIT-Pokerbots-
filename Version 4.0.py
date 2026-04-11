from pkbot.actions import ActionFold, ActionCall, ActionCheck, ActionRaise, ActionBid
from pkbot.states import GameInfo, PokerState
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot

from numpy import random
import eval7

DECK_STRINGS = [r+s for r in "23456789TJQKA" for s in "cdhs"]

ANY_TWO_CARDS = eval7.HandRange("22+, A2+, K2+, Q2+, J2+, T2+, 92+, 82+, 72+, 62+, 52+, 42+, 32+")
MEDIUM_RANGE = eval7.HandRange("22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 97s+, 87s, A2o+, K9o+, QTo+, JTo")
STRONG_RANGE = eval7.HandRange("55+, A4s+, K7s+, Q9s+, J9s+, T9s, A9o+, KTo+, QJo")
PREMIUM_RANGE = eval7.HandRange("77+, A9s+, KTs+, QJs, AJo+, KQo")

dic = {'A':14, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13}
PREFLOP_RANKS= {
    "AA": 1, "KK": 2, "QQ": 3, "AKs": 4, "JJ": 5, "AQs": 6, "KQs": 7,
    "AJs": 8, "KJs": 9, "TT": 10, "AKo": 11, "ATs": 12, "QJs": 13, "KTs": 14,
    "QTs": 15, "JTs": 16, "99": 17, "AQo": 18, "A9s": 19, "KQo": 20, "88": 21,
    "K9s": 22, "T9s": 23, "A8s": 24, "Q9s": 25, "J9s": 26, "AJo": 27, "A5s": 28,
    "77": 29, "A7s": 30, "KJo": 31, "A4s": 32, "A3s": 33, "A6s": 34, "QJo": 35,
    "66": 36, "K8s": 37, "T8s": 38, "A2s": 39, "98s": 40, "J8s": 41, "ATo": 42,
    "Q8s": 43, "K7s": 44, "KTo": 45, "55": 46, "JTo": 47, "87s": 48, "QTo": 49,
    "44": 50, "33": 51, "22": 52, "K6s": 53, "97s": 54, "K5s": 55, "76s": 56,
    "T7s": 57, "K4s": 58, "K3s": 59, "K2s": 60, "Q7s": 61, "86s": 62, "65s": 63,
    "J7s": 64, "54s": 65, "Q6s": 66, "75s": 67, "96s": 68, "Q5s": 69, "64s": 70,
    "Q4s": 71, "Q3s": 72, "T9o": 73, "T6s": 74, "Q2s": 75, "A9o": 76, "53s": 77,
    "85s": 78, "J6s": 79, "J9o": 80, "K9o": 81, "J5s": 82, "Q9o": 83, "43s": 84,
    "74s": 85, "J4s": 86, "J3s": 87, "95s": 88, "J2s": 89, "63s": 90, "A8o": 91,
    "52s": 92, "T5s": 93, "84s": 94, "T4s": 95, "T3s": 96, "42s": 97, "T2s": 98,
    "98o": 99, "T8o": 100, "A5o": 101, "A7o": 102, "73s": 103, "A4o": 104,
    "32s": 105, "94s": 106, "93s": 107, "J8o": 108, "A3o": 109, "62s": 110,
    "92s": 111, "K8o": 112, "A6o": 113, "87o": 114, "Q8o": 115, "83s": 116,
    "A2o": 117, "82s": 118, "97o": 119, "72s": 120, "76o": 121, "K7o": 122,
    "65o": 123, "T7o": 124, "K6o": 125, "86o": 126, "54o": 127, "K5o": 128,
    "J7o": 129, "75o": 130, "Q7o": 131, "K4o": 132, "K3o": 133, "96o": 134,
    "K2o": 135, "64o": 136, "Q6o": 137, "53o": 138, "85o": 139, "T6o": 140,
    "Q5o": 141, "43o": 142, "Q4o": 143, "Q3o": 144, "74o": 145, "Q2o": 146,
    "J6o": 147, "63o": 148, "J5o": 149, "95o": 150, "52o": 151, "J4o": 152,
    "J3o": 153, "42o": 154, "J2o": 155, "84o": 156, "T5o": 157, "T4o": 158,
    "32o": 159, "T3o": 160, "73o": 161, "T2o": 162, "62o": 163, "94o": 164,
    "93o": 165, "92o": 166, "83o": 167, "82o": 168, "72o": 169,
}

class Player(BaseBot):

    def __init__(self) -> None:
        self.alpha = 0.15
        self.won_auction_this_round = False
        self.auc_won = 0
        self.opp_range = ANY_TWO_CARDS
        self.cached_equity = 0.0
        self.cached_street = None
        self.cached_opp_range = None
        

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.opp_range = ANY_TWO_CARDS
        self.cached_street = None
        self.cached_opp_range = None
        self.won_auction_this_round = False
        if (game_info.round_num % 20 == 0):
            if (self.auc_won >= 18): self.alpha = min(0.15, self.alpha - 0.1)
            elif (self.auc_won <= 2): 
                self.alpha += 0.25
            elif (self.auc_won <= 7):
                self.alpha += 0.1  
            self.auc_won = 0
            self.alpha = min(2.5, self.alpha)

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        pass

    def get_move(self, game_info: GameInfo, current_state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        my_cards = current_state.my_hand

        C1N = my_cards[0][0]
        C2N = my_cards[1][0]
        C1S = my_cards[0][1]
        C2S = my_cards[1][1]

        base_pot = max(1, current_state.pot - current_state.opp_wager)
        bet_ratio = current_state.opp_wager / base_pot
        
        if current_state.street == 'auction':
            hero_hand = [eval7.Card(c) for c in my_cards]
            board_cards = [eval7.Card(c) for c in current_state.board]
            equity = eval7.py_hand_vs_range_monte_carlo(hero_hand,self.opp_range, board_cards, 16000)
            mult = (((2.71**equity) + (2.71**(1-equity))) * min(equity, 1-equity)) / 1.65
            bid = int(current_state.pot * self.alpha * mult + random.randint(1, 4))
            return ActionBid(int(max(0, min(bid, current_state.my_chips))))
        
        if current_state.street == 'pre-flop':
            stt = '' if C1N == C2N else 's' if C1S == C2S else 'o'
            if (dic[C1N] > dic[C2N]): s = C1N + C2N + stt
            else: s = C2N + C1N + stt
            rank = PREFLOP_RANKS[s]
            
            is_opening = current_state.opp_wager <= 20 
            facing_raise = current_state.opp_wager > 20
            high_raise = current_state.opp_wager > 80
            ultra_raise = current_state.opp_wager > 200
            if ultra_raise: self.opp_range = PREMIUM_RANGE
            elif high_raise: self.opp_range = STRONG_RANGE

            
            if current_state.can_act(ActionRaise):
                min_raise, max_raise = current_state.raise_bounds
                standard_open = int(min(max_raise, max(min_raise, 60))) 
                three_bet_size = int(min(max_raise, max(min_raise, current_state.opp_wager * 3)))
            else:
                standard_open = 0
                three_bet_size = 0
            
            if rank <= 2:
                if facing_raise and current_state.can_act(ActionRaise):
                    return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise):
                    return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall):
                    return ActionCall()
            
            elif rank <= 4:
                if ultra_raise: 
                    if current_state.can_act(ActionCall): return ActionCall()
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    return ActionFold() 
                
                if facing_raise and current_state.can_act(ActionRaise):
                    return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise):
                    return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall):
                    return ActionCall()
            
            if rank <= 16:
                if ultra_raise: 
                    if (random.random() < 0.05 and current_state.can_act(ActionRaise)): return ActionRaise(min_raise) 
                    if current_state.can_act(ActionFold): return ActionFold()
                if high_raise and current_state.can_act(ActionCall):
                    if (random.random() < 0.08 and current_state.can_act(ActionRaise)): return ActionRaise(min_raise)
                    return ActionCall()
                if high_raise: return ActionFold()
                if facing_raise and current_state.can_act(ActionRaise):
                    return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise):
                    return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall):
                    return ActionCall()
                    
            elif rank <= 55:
                if facing_raise:
                    if (not high_raise) and random.random() < 0.08 and current_state.can_act(ActionRaise): 
                        return ActionRaise(three_bet_size)
                    if current_state.can_act(ActionCall):
                        return ActionCall()
                else:
                    if current_state.can_act(ActionRaise):
                        return ActionRaise(standard_open) 
                        
            elif rank <= 99:
                if facing_raise:
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    return ActionFold() 
                else:
                    if is_opening and current_state.can_act(ActionRaise):
                        return ActionRaise(standard_open)
                    if current_state.can_act(ActionCheck):
                        return ActionCheck() 
                    if current_state.can_act(ActionCall):
                        return ActionCall()
                        
            else:
                if current_state.can_act(ActionCheck):
                    return ActionCheck() 
                return ActionFold()
        
        if current_state.street == 'flop':
            if bet_ratio >= 1:
                self.opp_range = PREMIUM_RANGE
            elif bet_ratio >=0.75 and self.opp_range != PREMIUM_RANGE:
                self.opp_range = STRONG_RANGE
            elif bet_ratio >= 0.4 and self.opp_range == ANY_TWO_CARDS:
                self.opp_range = MEDIUM_RANGE
                
            if current_state.street != self.cached_street or self.opp_range != self.cached_opp_range:
                hero_hand = [eval7.Card(c) for c in my_cards]
                board_cards = [eval7.Card(c) for c in current_state.board]
            
                if (current_state.opp_revealed_cards != []):
                    if not self.won_auction_this_round:
                        self.auc_won += 1
                        self.won_auction_this_round = True
                    
                    range_str = ",".join([current_state.opp_revealed_cards[0] + c for c in DECK_STRINGS if c != current_state.opp_revealed_cards[0]])
                    equity = eval7.py_hand_vs_range_monte_carlo(hero_hand, eval7.HandRange(range_str), board_cards, 16000)
                else:
                    equity = eval7.py_hand_vs_range_monte_carlo(hero_hand, self.opp_range, board_cards, 16000)
                
                self.cached_equity = equity
                self.cached_street = current_state.street
                self.cached_opp_range = self.opp_range
            
            else:
                equity = self.cached_equity

            heavy_agg = bet_ratio > 0.8
            ultra_heavy_agg = bet_ratio > 1.2

            score = eval7.evaluate([eval7.Card(c) for c in my_cards + current_state.board])
            hand_string = eval7.handtype(score) 

            weak_hand_types = ["High Card", "Pair"]
            is_weak_hand = hand_string in weak_hand_types

            if heavy_agg and hand_string == "High Card":
                if current_state.can_act(ActionFold): return ActionFold()

            if equity > 0.85:
                if ultra_heavy_agg and is_weak_hand: 
                     if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionRaise): 
                    raise_amt = int(max(current_state.raise_bounds[0], min(current_state.raise_bounds[1], current_state.pot * 0.75)))
                    return ActionRaise(raise_amt)
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
                return ActionFold()
            
            if ultra_heavy_agg and is_weak_hand:
                if current_state.can_act(ActionFold): return ActionFold()
            
            if equity > 0.65:
                if ultra_heavy_agg:
                    if current_state.can_act(ActionFold): return ActionFold()
                if heavy_agg:
                    if current_state.can_act(ActionCall): return ActionCall()
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    return ActionFold()
                if current_state.can_act(ActionRaise):
                    if random.random() > 0.8:
                        raise_amt = int(max(current_state.raise_bounds[0], min(current_state.raise_bounds[1], current_state.pot * 0.5)))
                        return ActionRaise(raise_amt)
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
                return ActionFold()
            
            if ultra_heavy_agg: return ActionFold()

            cost = current_state.cost_to_call
            total_reward = current_state.pot + cost 
            pot_odds = cost / total_reward if total_reward > 0 else 0
            
            if cost > 0 and equity >= (pot_odds + 0.05):
                if current_state.can_act(ActionCall): return ActionCall()
            elif cost > 0:
                if current_state.can_act(ActionFold): return ActionFold()

            if current_state.can_act(ActionCheck): return ActionCheck()
            if current_state.can_act(ActionFold): return ActionFold()
        
        if current_state.street in ['turn', 'river']:
            if bet_ratio >= 1:
                self.opp_range = PREMIUM_RANGE
            elif bet_ratio >=0.75 and self.opp_range != PREMIUM_RANGE:
                self.opp_range = STRONG_RANGE
            elif bet_ratio >= 0.4 and self.opp_range == ANY_TWO_CARDS:
                self.opp_range = MEDIUM_RANGE

            if current_state.street != self.cached_street or self.opp_range != self.cached_opp_range:
                if (current_state.opp_revealed_cards != []): 
                    hero = [eval7.Card(c) for c in my_cards]
                    board = [eval7.Card(c) for c in current_state.board]
    
                    range_str = ",".join([current_state.opp_revealed_cards[0] + c for c in DECK_STRINGS if c != current_state.opp_revealed_cards[0]])
                    equity = eval7.py_hand_vs_range_exact(hero, eval7.HandRange(range_str), board)
                else:
                    hero = [eval7.Card(c) for c in my_cards]
                    board = [eval7.Card(c) for c in current_state.board]
    
                    if (current_state.street == "turn"): equity = eval7.py_hand_vs_range_monte_carlo(hero, self.opp_range, board, 16000)
                    else: equity = eval7.py_hand_vs_range_exact(hero, self.opp_range, board)
                    
                self.cached_equity = equity
                self.cached_street = current_state.street
                self.cached_opp_range = self.opp_range
            
            else: equity = self.cached_equity

            heavy_agg = bet_ratio > 0.8
            ultra_heavy_agg = bet_ratio > 1.2
            
            score = eval7.evaluate([eval7.Card(c) for c in my_cards + current_state.board])
            hand_string = eval7.handtype(score) 

            weak_hand_types = ["High Card", "Pair"]
            is_weak_hand = hand_string in weak_hand_types

            if ultra_heavy_agg and is_weak_hand:
                if current_state.can_act(ActionFold): return ActionFold()
                
            if heavy_agg and hand_string == "High Card":
                if current_state.can_act(ActionFold): return ActionFold()

            if equity > 0.85:
                if ultra_heavy_agg and is_weak_hand: 
                     if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionRaise): 
                    raise_amt = int(max(current_state.raise_bounds[0], min(current_state.raise_bounds[1], current_state.pot * 0.75)))
                    return ActionRaise(raise_amt)
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
                return ActionFold()
            
            if equity > 0.65:
                if ultra_heavy_agg:
                    if current_state.can_act(ActionFold): return ActionFold()
                if heavy_agg:
                    if current_state.can_act(ActionCall): return ActionCall()
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    return ActionFold()
                if current_state.can_act(ActionRaise):
                    if random.random() > 0.8:
                        raise_amt = int(max(current_state.raise_bounds[0], min(current_state.raise_bounds[1], current_state.pot * 0.5)))
                        return ActionRaise(raise_amt)
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
                return ActionFold()
            
            if ultra_heavy_agg: return ActionFold()

            cost = current_state.cost_to_call
            total_reward = current_state.pot + cost 
            pot_odds = cost / total_reward if total_reward > 0 else 0
            
            if cost > 0 and equity >= (pot_odds + 0.05):
                if current_state.can_act(ActionCall): return ActionCall()
            elif cost > 0:
                if current_state.can_act(ActionFold): return ActionFold()

            if current_state.can_act(ActionCheck): return ActionCheck()
            if current_state.can_act(ActionFold): return ActionFold()
        

        if current_state.can_act(ActionCheck):
            return ActionCheck()
        if current_state.can_act(ActionCall):
            return ActionCall()
        return ActionFold()

if __name__ == '__main__':
    run_bot(Player(), parse_args())