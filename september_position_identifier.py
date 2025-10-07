from datetime import datetime
import pandas as pd
import numpy as np
import sys
from fibo_calculate import fibonacci_retracement
from get_legs import get_legs
from swing import get_swing_points
from utils import BotState


class SeptemberPositionIdentifier:
    def __init__(self, data):
        self.data = data.copy()
        self.data['status'] = np.where(self.data['open'] > self.data['close'], 'bearish', 'bullish')
        self.positions = []
        self.state = BotState()
        self.last_swing_type = None
        self.active_fib_anchor = None
        
    def identify_positions(self):
        print("🔍 شروع شناسایی پوزیشن‌ها برای کل ماه سپتامبر...")
        for i in range(200, len(self.data)):
            current_data = self.data.iloc[: i + 1].copy()
            self._process_data_point(current_data, i)
        return self.positions
    
    def _process_data_point(self, data, current_index):
        try:
            legs = get_legs(data)
            
            if len(legs) > 2:
                legs = legs[-3:]
                swing_type, is_swing = get_swing_points(data, legs)
                
                if is_swing:
                    if not self.state.fib_levels:
                        self._create_new_fibonacci(legs, swing_type, data.index[-1])
                    elif self.state.second_touch:
                        current_candle = data.iloc[-1]
                        self._create_position(swing_type, current_candle)
                
                if self.state.fib_levels:
                    self._check_fibonacci_updates(data, swing_type)
            
            if len(legs) < 3 and self.state.fib_levels:
                self._check_fibonacci_updates(data, self.last_swing_type)
            
            if self.state.fib_levels:
                self._check_705_touches(data, current_index)
                
        except Exception as e:
            print(f"❌ خطا در پردازش ایندکس {current_index}: {e}")
    
    def _create_new_fibonacci(self, legs, swing_type, timestamp):
        self.state.reset()
        self.state.fib_levels = fibonacci_retracement(
            start_price=legs[2]['end_value'], 
            end_price=legs[2]['start_value']
        )
        self.state.fib1_time = legs[2]['start']
        self.state.fib0_time = legs[2]['end']
        self.last_swing_type = swing_type
        self.active_fib_anchor = (legs[2]['start'], legs[2]['end'])
        
        print(f"📈 فیبوناچی جدید ایجاد شد در {timestamp}: {swing_type}")
        print(f"   Fib 0: {self.state.fib_levels['0.0']:.5f}")
        print(f"   Fib 0.705: {self.state.fib_levels['0.705']:.5f}")
        print(f"   Fib 1: {self.state.fib_levels['1.0']:.5f}")
    
    def _check_fibonacci_updates(self, data, swing_type):
        if not self.state.fib_levels:
            return
            
        current_candle = data.iloc[-2]
        
        if swing_type == 'bullish':
            if current_candle['high'] > self.state.fib_levels['0.0']:
                self.state.fib_levels = fibonacci_retracement(
                    start_price=current_candle['high'], 
                    end_price=self.state.fib_levels['1.0']
                )
                self.state.fib0_time = current_candle.name
                print(f"📈 فیبوناچی آپدیت شد (عبور از fib 0)")
            elif current_candle['low'] < self.state.fib_levels['1.0']:
                self.state.reset()
                self.active_fib_anchor = None
                print(f"❌ فیبوناچی نقض شد (زیر fib 1)")
                return
            elif current_candle['low'] <= self.state.fib_levels['0.705']:
                self._handle_705_touch(current_candle, swing_type)
        
        elif swing_type == 'bearish':
            if current_candle['low'] < self.state.fib_levels['0.0']:
                self.state.fib_levels = fibonacci_retracement(
                    start_price=current_candle['low'], 
                    end_price=self.state.fib_levels['1.0']
                )
                self.state.fib0_time = current_candle.name
                print(f"📉 فیبوناچی آپدیت شد (عبور از fib 0)")
            elif current_candle['high'] > self.state.fib_levels['1.0']:
                self.state.reset()
                self.active_fib_anchor = None
                print(f"❌ فیبوناچی نقض شد (بالای fib 1)")
                return
            elif current_candle['high'] >= self.state.fib_levels['0.705']:
                self._handle_705_touch(current_candle, swing_type)
    
    def _handle_705_touch(self, candle, swing_type):
        if not self.state.first_touch:
            self.state.first_touch = True
            self.state.first_touch_value = candle
            print(f"👆 اولین touch در 0.705: {candle.name} - {swing_type}")
        elif self.state.first_touch and not self.state.second_touch:
            if candle['status'] != self.state.first_touch_value['status']:
                self.state.second_touch = True
                self.state.second_touch_value = candle
                print(f"✌️ دومین touch در 0.705: {candle.name} - {candle['status']}")
    
    def _create_position(self, swing_type, entry_candle):
        if not self.state.fib_levels:
            return
            
        fib_levels = self.state.fib_levels
        fib_0 = fib_levels['0.0']
        fib_1 = fib_levels['1.0']
        fib_09 = fib_levels['0.9']
        
        entry_price = entry_candle['close']
        
        pip_size = 0.0001
        two_pips = 2.0 * pip_size
        
        if swing_type == 'bullish':
            is_close_to_09 = abs(fib_09 - entry_price) <= two_pips
            candidate_sl = fib_1 if is_close_to_09 else fib_09
            if candidate_sl >= entry_price:
                return
            stop_distance = abs(entry_price - candidate_sl)
            tp_price = entry_price + (stop_distance * 1.2)
            position_type = 'BUY'
        else:
            is_close_to_09 = abs(fib_09 - entry_price) <= two_pips
            candidate_sl = fib_1 if is_close_to_09 else fib_09
            if candidate_sl <= entry_price:
                return
            stop_distance = abs(entry_price - candidate_sl)
            tp_price = entry_price - (stop_distance * 1.2)
            position_type = 'SELL'
        
        position = {
            'position_id': len(self.positions) + 1,
            'timestamp': entry_candle.name,
            'swing_type': swing_type,
            'position_type': position_type,
            'fib_0': fib_0,
            'fib_1': fib_1,
            'fib_705': fib_levels['0.705'],
            'fib_09': fib_09,
            'first_touch_time': self.state.first_touch_value.name,
            'first_touch_price': self.state.first_touch_value['close'],
            'second_touch_time': self.state.second_touch_value.name,
            'second_touch_price': self.state.second_touch_value['close'],
            'entry_price': entry_price,
            'sl_price': candidate_sl,
            'tp_price': tp_price,
            'risk_reward_ratio': 1.2,
            'fib_creation_time': self.state.fib0_time,
            'fib_end_time': self.state.fib1_time,
            'fib_valid': True
        }
        
        self.positions.append(position)
        print(f"✅ پوزیشن ایجاد شد: {position_type} در {entry_price:.5f}")
        
        self.state.reset()
    
    def _check_705_touches(self, data, current_index):
        if not self.state.fib_levels:
            return
            
        current_candle = data.iloc[-1]
        
        if self.last_swing_type == 'bullish':
            if current_candle['low'] <= self.state.fib_levels['0.705']:
                self._handle_705_touch(current_candle, self.last_swing_type)
        elif self.last_swing_type == 'bearish':
            if current_candle['high'] >= self.state.fib_levels['0.705']:
                self._handle_705_touch(current_candle, self.last_swing_type)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("🚀 شروع سیستم شناسایی پوزیشن‌ها برای سپتامبر 2025")
    
    # بارگذاری از CSV ماهانه
    try:
        data = pd.read_csv('M1_data_EURUSD_2025-09.csv')
        data['time'] = pd.to_datetime(data['time'])
        data.set_index('time', inplace=True)
        print(f"📊 {len(data)} نقطه داده بارگذاری شد")
    except Exception as e:
        print(f"❌ خطا در بارگذاری داده‌ها: {e}")
        return
    
    identifier = SeptemberPositionIdentifier(data)
    positions = identifier.identify_positions()
    
    print(f"\n📈 {len(positions)} پوزیشن معتبر شناسایی شد:")
    print("=" * 100)
    
    # گروه‌بندی پوزیشن‌ها بر اساس روز
    positions_df = pd.DataFrame(positions)
    if not positions_df.empty:
        positions_df['date'] = pd.to_datetime(positions_df['timestamp']).dt.date
        days = positions_df['date'].unique()
        
        for day in sorted(days):
            day_positions = positions_df[positions_df['date'] == day]
            print(f"\n📅 روز {day}:")
            print(f"تعداد پوزیشن‌ها: {len(day_positions)}")
            print("-" * 80)
            
            for _, pos in day_positions.iterrows():
                print(f"\n🔹 پوزیشن #{int(pos['position_id'])}:")
                print(f"   زمان: {pos['timestamp']}")
                print(f"   نوع: {pos['position_type']} ({pos['swing_type']} swing)")
                print(f"   ورود: {pos['entry_price']:.5f}")
                print(f"   SL: {pos['sl_price']:.5f}")
                print(f"   TP: {pos['tp_price']:.5f}")
                print(f"   سطوح فیبوناچی:")
                print(f"     - Fib 0: {pos['fib_0']:.5f}")
                print(f"     - Fib 0.705: {pos['fib_705']:.5f}")
                print(f"     - Fib 0.9: {pos['fib_09']:.5f}")
                print(f"     - Fib 1: {pos['fib_1']:.5f}")
                print(f"   نقاط لمس:")
                print(f"     - اولین لمس: {pos['first_touch_time']} در {pos['first_touch_price']:.5f}")
                print(f"     - دومین لمس: {pos['second_touch_time']} در {pos['second_touch_price']:.5f}")
                print(f"   نسبت ریسک/پاداش: {pos['risk_reward_ratio']}")
                print("-" * 60)
    
    # ذخیره نتایج
    if positions:
        df_positions = pd.DataFrame(positions)
    else:
        df_positions = pd.DataFrame(columns=[
            'position_id','timestamp','swing_type','position_type','fib_0','fib_1','fib_705','fib_09',
            'first_touch_time','first_touch_price','second_touch_time','second_touch_price',
            'entry_price','sl_price','tp_price','risk_reward_ratio','fib_creation_time','fib_end_time','fib_valid'
        ])
    df_positions.to_csv('september_positions.csv', index=False)
    print(f"\n💾 پوزیشن‌ها در 'september_positions.csv' ذخیره شد")
    
    print(f"\n✅ شناسایی پوزیشن‌ها تکمیل شد!")


if __name__ == "__main__":
    main()