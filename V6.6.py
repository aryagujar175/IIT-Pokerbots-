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
        self.street_raise_count = 0 
        
        # Opponent Profiling Dictionary
        self.opp_profile = {
            "hands_played": 0,
            "overbets_made": 0,
            "bluffs_shown": 0,      # Times they showed up with a weak hand after an overbet
            "preflop_raises": 0,    # Times they raised preflop (to catch blind stealers)
            "vpip": 0               # Voluntarily Put in Pot (called or raised preflop)
        }
        
        # Per-hand tracking flags
        self.faced_overbet_this_hand = False
        self.opp_voluntarily_entered = False
        self.opp_raised_preflop = False
        
    def _is_board_wet(self, board_cards):
        """ Analyzes the board for straight and flush threats. """
        if len(board_cards) < 3: return False
        
        suits = [c.suit for c in board_cards]
        ranks = sorted([c.rank for c in board_cards])
        
        # 1. Flush Danger: 3 or more of the same suit
        suit_counts = [suits.count(s) for s in set(suits)]
        if max(suit_counts) >= 3:
            return True
            
        # 2. Straight Danger: 3 cards within a 4-rank spread (e.g., 5, 7, 8)
        for i in range(len(ranks) - 2):
            if ranks[i+2] - ranks[i] <= 3:
                return True
                
        # 3. Straight Danger: 4 cards within a 5-rank spread (Turn/River)
        if len(ranks) >= 4:
            for i in range(len(ranks) - 3):
                if ranks[i+3] - ranks[i] <= 4:
                    return True
                    
        return False

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.opp_range = ANY_TWO_CARDS
        self.cached_street = None
        self.cached_opp_range = None
        self.won_auction_this_round = False
        self.street_raise_count = 0  
        
        # Reset tracking flags for the new hand
        self.faced_overbet_this_hand = False
        self.opp_voluntarily_entered = False
        self.opp_raised_preflop = False
        self.opp_profile["hands_played"] += 1
        
        # VERSION 4.0 DYNAMIC ALPHA ADJUSTMENT
        if (game_info.round_num % 20 == 0):
            if (self.auc_won >= 18): self.alpha = min(0.15, self.alpha - 0.1)
            elif (self.auc_won <= 2): 
                self.alpha += 0.25
            elif (self.auc_won <= 7):
                self.alpha += 0.1  
            self.auc_won = 0
            self.alpha = min(2.5, self.alpha)

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        if self.opp_voluntarily_entered:
            self.opp_profile["vpip"] += 1
        
        if self.opp_raised_preflop:
            self.opp_profile["preflop_raises"] += 1
            
        if self.faced_overbet_this_hand:
            self.opp_profile["overbets_made"] += 1
            
            if len(current_state.opp_revealed_cards) >= 2:
                score = eval7.evaluate([eval7.Card(c) for c in current_state.opp_revealed_cards + current_state.board])
                hand_type = eval7.handtype(score)
                
                if hand_type in ["High Card", "Pair"]:
                    self.opp_profile["bluffs_shown"] += 1

    def get_move(self, game_info: GameInfo, current_state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        my_cards = current_state.my_hand

        C1N = my_cards[0][0]
        C2N = my_cards[1][0]
        C1S = my_cards[0][1]
        C2S = my_cards[1][1]

        base_pot = max(1, current_state.pot - current_state.opp_wager)
        bet_ratio = current_state.opp_wager / base_pot
        
        if bet_ratio >= 1:
            self.faced_overbet_this_hand = True
            
        if current_state.street == 'pre-flop' and current_state.opp_wager > 20:
            self.opp_voluntarily_entered = True
            self.opp_raised_preflop = True
        
        # --- RESTORED VERSION 4.0 AUCTION BIDS ---
        if current_state.street == 'auction':
            hero_hand = [eval7.Card(c) for c in my_cards]
            board_cards = [eval7.Card(c) for c in current_state.board]
            equity = eval7.py_hand_vs_range_monte_carlo(hero_hand, self.opp_range, board_cards, 16000)
            
            # Mathematical curve from V4.0
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
            
            # --- BLIND STEAL DEFENSE: DETECT MANIAC OPENS ---
            opp_is_maniac = False
            if self.opp_profile["hands_played"] > 10:
                if (self.opp_profile["preflop_raises"] / max(1, self.opp_profile["hands_played"])) > 0.6:
                    opp_is_maniac = True

            if current_state.can_act(ActionRaise):
                min_raise, max_raise = current_state.raise_bounds
                bb = 20
                base_open = 48 
                three_bet_mult = 3.0
                
                if self.opp_profile["hands_played"] > 15:
                    vpip_rate = self.opp_profile["vpip"] / max(1, self.opp_profile["hands_played"])
                    if vpip_rate > 0.45:
                        if rank <= 16:
                            base_open = 70
                            three_bet_mult = 3.8
                    elif vpip_rate < 0.20:
                        base_open = 42
                        three_bet_mult = 2.6
                
                jitter = random.randint(-3, 3)
                target_open = base_open + jitter
                target_3bet = int(current_state.opp_wager * three_bet_mult) + jitter
                
                standard_open = int(max(min_raise, min(max_raise, target_open))) 
                three_bet_size = int(max(min_raise, min(max_raise, target_3bet)))
            else:
                standard_open = 0
                three_bet_size = 0
            
            if rank <= 2:
                if facing_raise and current_state.can_act(ActionRaise): return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise): return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall): return ActionCall()
            
            elif rank <= 4:
                if ultra_raise: 
                    if current_state.can_act(ActionCall): return ActionCall()
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    return ActionFold() 
                
                if facing_raise and current_state.can_act(ActionRaise): return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise): return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall): return ActionCall()
            
            elif rank <= 16:
                if ultra_raise: 
                    if (random.random() < 0.05 and current_state.can_act(ActionRaise)): return ActionRaise(min_raise) 
                    if current_state.can_act(ActionFold): return ActionFold()
                if high_raise and current_state.can_act(ActionCall):
                    if (random.random() < 0.08 and current_state.can_act(ActionRaise)): return ActionRaise(min_raise)
                    return ActionCall()
                if high_raise: return ActionFold()
                if facing_raise and current_state.can_act(ActionRaise): return ActionRaise(three_bet_size) 
                elif current_state.can_act(ActionRaise): return ActionRaise(standard_open)  
                elif current_state.can_act(ActionCall): return ActionCall()
                    
            elif rank <= 55:
                if facing_raise:
                    if not high_raise:
                        # Exploit: 3-bet the maniac to extract value and force folds
                        if opp_is_maniac and current_state.can_act(ActionRaise) and random.random() < 0.6:
                            return ActionRaise(three_bet_size)
                        elif random.random() < 0.08 and current_state.can_act(ActionRaise): 
                            return ActionRaise(three_bet_size)
                    if current_state.can_act(ActionCall): return ActionCall()
                else:
                    if current_state.can_act(ActionRaise): return ActionRaise(standard_open) 
            
            elif rank <= 85:
                # Exploit: Defend blinds wider against Maniac
                if facing_raise and opp_is_maniac and not high_raise:
                    if current_state.can_act(ActionCall): return ActionCall()
                    
                if current_state.cost_to_call > 0:
                    if current_state.can_act(ActionFold): return ActionFold()
                if current_state.can_act(ActionCheck): return ActionCheck() 
                return ActionFold()
                
            else:
                if current_state.cost_to_call > 0:
                    if current_state.can_act(ActionFold): return ActionFold()
                if current_state.can_act(ActionCheck): return ActionCheck() 
                return ActionFold()
        
        if current_state.street in ['flop', 'turn', 'river']:
            if bet_ratio >= 1:
                if self.opp_profile["overbets_made"] >= 5: 
                    bluff_freq = self.opp_profile["bluffs_shown"] / max(1, self.opp_profile["overbets_made"])
                    if bluff_freq > 0.3: self.opp_range = MEDIUM_RANGE
                    else: self.opp_range = PREMIUM_RANGE
                else: self.opp_range = PREMIUM_RANGE
            elif bet_ratio >= 0.75 and self.opp_range != PREMIUM_RANGE:
                self.opp_range = STRONG_RANGE
            elif bet_ratio >= 0.4 and self.opp_range == ANY_TWO_CARDS:
                self.opp_range = MEDIUM_RANGE

            if current_state.street != self.cached_street or self.opp_range != self.cached_opp_range:
                if current_state.street != self.cached_street:
                    self.street_raise_count = 0
                
                hero = [eval7.Card(c) for c in my_cards]
                board = [eval7.Card(c) for c in current_state.board]
            
                if (current_state.opp_revealed_cards != []):
                    if current_state.street == 'flop' and not self.won_auction_this_round:
                        self.auc_won += 1
                        self.won_auction_this_round = True
                    
                    # --- FIX 1: INTERSECT REVEALED CARD WITH CURRENT RANGE ---
                    rev_card_str = current_state.opp_revealed_cards[0]
                    valid_hands = []
                    
                    for hand in self.opp_range:
                        # hand is a tuple of eval7.Card, we check if the revealed card matches either
                        if str(hand[0]) == rev_card_str or str(hand[1]) == rev_card_str:
                            valid_hands.append(str(hand[0]) + str(hand[1]))
                    
                    if valid_hands:
                        calc_range = eval7.HandRange(",".join(valid_hands))
                    else:
                        # Fallback if the opponent's card completely breaks our read (e.g. random bluff)
                        range_str = ",".join([rev_card_str + c for c in DECK_STRINGS if c != rev_card_str])
                        calc_range = eval7.HandRange(range_str)
                else:
                    calc_range = self.opp_range
                
                if current_state.street == 'river' or (current_state.street == 'turn' and current_state.opp_revealed_cards != []): 
                    equity = eval7.py_hand_vs_range_exact(hero, calc_range, board)
                else:
                    equity = eval7.py_hand_vs_range_monte_carlo(hero, calc_range, board, 16000)
                
                self.cached_equity = equity
                self.cached_street = current_state.street
                self.cached_opp_range = self.opp_range
            else:
                equity = self.cached_equity

            heavy_agg = bet_ratio > 0.75
            ultra_heavy_agg = bet_ratio > 1.2
            
            score = eval7.evaluate([eval7.Card(c) for c in my_cards + current_state.board])
            hand_string = eval7.handtype(score) 

            cost = current_state.cost_to_call
            total_reward = current_state.pot + cost 
            pot_odds = cost / total_reward if total_reward > 0 else 0

            # Board Texture Pot Control
            board_eval = [eval7.Card(c) for c in current_state.board]
            board_is_wet = self._is_board_wet(board_eval)
            allow_raise = True
            
            # If the board has high straight/flush danger and we don't have a made Straight/Flush, disable raising
            if board_is_wet and hand_string in ["High Card", "Pair", "Two Pair", "Three of a Kind"]:
                allow_raise = False

            # Calling Station Hard Folds
            if current_state.street in ['turn', 'river'] and cost > 0:
                if hand_string in ["High Card", "Pair"]:
                    if current_state.street == 'river' and bet_ratio >= 0.5:
                        if current_state.can_act(ActionFold): return ActionFold()
                    elif current_state.street == 'turn' and bet_ratio >= 0.75:
                        if current_state.can_act(ActionFold): return ActionFold()

            if current_state.opp_wager == 0:
                if equity > 0.85:
                    if allow_raise and current_state.can_act(ActionRaise):
                        target_raise = int(current_state.pot * 0.6)
                        min_r, max_r = current_state.raise_bounds
                        meaningful_raise = max(target_raise, int(min_r * 1.5))
                        bet_amt = int(max(min_r, min(max_r, meaningful_raise)))
                        
                        if self.street_raise_count >= 2 and equity < 0.95:
                            if current_state.can_act(ActionCall): return ActionCall()
                            if current_state.can_act(ActionCheck): return ActionCheck()
                        self.street_raise_count += 1
                        return ActionRaise(bet_amt)
                        
                elif equity > 0.6:
                    if allow_raise and current_state.can_act(ActionRaise) and random.random() < 0.25:
                        target_raise = int(current_state.pot * 0.4)
                        min_r, max_r = current_state.raise_bounds
                        meaningful_raise = max(target_raise, int(min_r * 1.5))
                        bet_amt = int(max(min_r, min(max_r, meaningful_raise)))
                        
                        if self.street_raise_count >= 2:
                            if current_state.can_act(ActionCall): return ActionCall()
                            if current_state.can_act(ActionCheck): return ActionCheck()
                        self.street_raise_count += 1
                        return ActionRaise(bet_amt)

            if ultra_heavy_agg:
                if hand_string in ["High Card", "Pair"]:
                    if equity < 0.8:
                        if current_state.can_act(ActionCheck): return ActionCheck()
                        if current_state.can_act(ActionFold): return ActionFold()
                if equity < 0.65:
                    if current_state.can_act(ActionCheck): return ActionCheck()
                    if current_state.can_act(ActionFold): return ActionFold()
            
            if heavy_agg:
                if hand_string == "High Card":
                    if current_state.can_act(ActionFold): return ActionFold()
                if hand_string == "Pair" and equity < 0.55:
                    if current_state.can_act(ActionFold): return ActionFold()

            if equity > 0.85:
                if allow_raise and current_state.can_act(ActionRaise): 
                    if current_state.opp_wager > 0:
                        base_pot = current_state.pot - current_state.opp_wager
                        target_raise = int(current_state.opp_wager * 3 + base_pot)
                    else:
                        target_raise = int(current_state.pot * 0.75)
                        
                    min_r, max_r = current_state.raise_bounds
                    meaningful_raise = max(target_raise, int(min_r * 1.5))
                    raise_amt = int(max(min_r, min(max_r, meaningful_raise)))
                    
                    if self.street_raise_count >= 2 and equity < 0.95:
                        if current_state.can_act(ActionCall): return ActionCall()
                        if current_state.can_act(ActionCheck): return ActionCheck()
                    self.street_raise_count += 1
                    return ActionRaise(raise_amt)
                    
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
            
            if equity > 0.65:
                if allow_raise and current_state.can_act(ActionRaise) and random.random() > 0.7:
                    if current_state.opp_wager > 0:
                        base_pot = current_state.pot - current_state.opp_wager
                        target_raise = int(current_state.opp_wager * 2.2 + base_pot) 
                    else:
                        target_raise = int(current_state.pot * 0.5)
                        
                    min_r, max_r = current_state.raise_bounds
                    meaningful_raise = max(target_raise, int(min_r * 1.5))
                    raise_amt = int(max(min_r, min(max_r, meaningful_raise)))
                    
                    if self.street_raise_count >= 2 and equity < 0.95:
                        if current_state.can_act(ActionCall): return ActionCall()
                        if current_state.can_act(ActionCheck): return ActionCheck()
                    self.street_raise_count += 1
                    return ActionRaise(raise_amt)
                    
                if current_state.can_act(ActionCall): return ActionCall()
                if current_state.can_act(ActionCheck): return ActionCheck()
            
            if cost > 0:
                margin = 0.05
                if heavy_agg: margin = 0.1
                if ultra_heavy_agg: margin = 0.15
                
                if equity >= (pot_odds + margin):
                    if current_state.can_act(ActionCall): return ActionCall()
                else:
                    if current_state.can_act(ActionFold): return ActionFold()

            if current_state.can_act(ActionCheck): return ActionCheck()
            if current_state.can_act(ActionFold): return ActionFold()
            
        if current_state.can_act(ActionCheck): return ActionCheck()
        if current_state.can_act(ActionCall): return ActionCall()
        return ActionFold()

if __name__ == '__main__':
    run_bot(Player(), parse_args())