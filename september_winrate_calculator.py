import pandas as pd
from datetime import datetime, time
import sys


def calculate_september_winrate():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("🚀 محاسبه وین‌ریت برای ماه سپتامبر 2025")

    # بارگذاری داده‌های تاریخی
    try:
        data = pd.read_csv('M1_data_EURUSD_2025-09.csv')
        data['time'] = pd.to_datetime(data['time'])
        data.set_index('time', inplace=True)
        print(f"📊 {len(data)} نقطه داده بارگذاری شد")
    except Exception as e:
        print(f"❌ خطا در بارگذاری داده‌ها: {e}")
        return

    # بارگذاری پوزیشن‌ها
    try:
        positions = pd.read_csv('september_positions.csv')
        positions['timestamp'] = pd.to_datetime(positions['timestamp'])
        print(f"📈 {len(positions)} پوزیشن بارگذاری شد")
    except Exception as e:
        print(f"❌ خطا در بارگذاری پوزیشن‌ها: {e}")
        return

    # فیلتر پوزیشن‌ها بر اساس زمان
    start_time = time(9, 0)
    end_time = time(20, 30)

    filtered_positions = positions[
        (positions['timestamp'].dt.time >= start_time) & 
        (positions['timestamp'].dt.time <= end_time)
    ].copy()

    print(f"\n🕐 فیلتر زمانی: 09:00 - 20:30")
    print(f"📊 پوزیشن‌های فیلتر شده: {len(filtered_positions)} از {len(positions)}")

    if len(filtered_positions) == 0:
        print("❌ هیچ پوزیشنی در بازه زمانی مشخص یافت نشد")
        pd.DataFrame(columns=['position_id','result','reason','hit_time']).to_csv('september_winrate_analysis.csv', index=False)
        return

    results = []
    daily_results = {}

    for _, pos in filtered_positions.iterrows():
        entry_time = pos['timestamp']
        entry_day = entry_time.date()
        entry_price = pos['entry_price']
        sl_price = pos['sl_price']
        tp_price = pos['tp_price']
        position_type = pos['position_type']

        print(f"\n🔍 بررسی پوزیشن #{pos['position_id']} در تاریخ {entry_day}:")
        print(f"   زمان ورود: {entry_time.strftime('%H:%M:%S')}")
        print(f"   نوع: {position_type}")
        print(f"   ورود: {entry_price:.5f}")
        print(f"   SL: {sl_price:.5f}")
        print(f"   TP: {tp_price:.5f}")

        # دریافت داده‌های آینده برای همان روز
        future_data = data[
            (data.index > entry_time) & 
            (data.index.date == entry_day)
        ]

        if len(future_data) == 0:
            results.append({
                'position_id': pos['position_id'], 
                'result': 'NO_DATA', 
                'reason': 'داده کافی موجود نیست',
                'hit_time': None,
                'trade_date': entry_day
            })
            continue

        result = 'UNKNOWN'
        reason = ''
        hit_time = None

        if position_type == 'BUY':
            for time_idx, candle in future_data.iterrows():
                if candle['high'] >= tp_price:
                    result = 'WIN'
                    reason = f'رسیدن به TP در {tp_price:.5f}'
                    hit_time = time_idx
                    break
                elif candle['low'] <= sl_price:
                    result = 'LOSS'
                    reason = f'رسیدن به SL در {sl_price:.5f}'
                    hit_time = time_idx
                    break
        elif position_type == 'SELL':
            for time_idx, candle in future_data.iterrows():
                if candle['low'] <= tp_price:
                    result = 'WIN'
                    reason = f'رسیدن به TP در {tp_price:.5f}'
                    hit_time = time_idx
                    break
                elif candle['high'] >= sl_price:
                    result = 'LOSS'
                    reason = f'رسیدن به SL در {sl_price:.5f}'
                    hit_time = time_idx
                    break

        if result == 'UNKNOWN':
            result = 'NO_HIT'
            reason = 'هیچ کدام از سطوح لمس نشده'

        results.append({
            'position_id': pos['position_id'],
            'result': result,
            'reason': reason,
            'hit_time': hit_time,
            'trade_date': entry_day
        })

        # اضافه کردن به نتایج روزانه
        if entry_day not in daily_results:
            daily_results[entry_day] = {'WIN': 0, 'LOSS': 0, 'NO_HIT': 0, 'NO_DATA': 0}
        daily_results[entry_day][result] += 1

    results_df = pd.DataFrame(results)
    results_df.to_csv('september_winrate_analysis.csv', index=False)
    print("\n💾 نتایج در 'september_winrate_analysis.csv' ذخیره شد")

    # نمایش نتایج روزانه
    print("\n📊 نتایج به تفکیک روز:")
    print("=" * 80)
    
    total_wins = 0
    total_losses = 0
    total_trades = 0
    
    for day in sorted(daily_results.keys()):
        day_stats = daily_results[day]
        day_total = sum(day_stats.values())
        day_wins = day_stats['WIN']
        day_losses = day_stats['LOSS']
        day_winrate = (day_wins / day_total * 100) if day_total > 0 else 0
        
        total_wins += day_wins
        total_losses += day_losses
        total_trades += day_total
        
        print(f"\n📅 {day}:")
        print(f"   معاملات: {day_total}")
        print(f"   برد: {day_wins}")
        print(f"   باخت: {day_losses}")
        print(f"   بدون نتیجه: {day_stats['NO_HIT']}")
        print(f"   وین‌ریت: {day_winrate:.1f}%")
        print("-" * 60)

    # نمایش نتایج کلی
    print("\n📈 نتایج کلی:")
    print("=" * 80)
    total_winrate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    print(f"📊 کل معاملات: {total_trades}")
    print(f"✅ تعداد برد: {total_wins}")
    print(f"❌ تعداد باخت: {total_losses}")
    print(f"📈 وین‌ریت کلی: {total_winrate:.1f}%")

    return total_winrate, total_wins, total_losses, total_trades


if __name__ == "__main__":
    calculate_september_winrate()