# check_status.py
import time
from config import Config
from multi_bot_manager import MultiBotManager

cfg = Config()
mgr = MultiBotManager(cfg)
mgr.initialize_bots()

# لو البوتات شغّالة من قبل فهنا بنسأل الحالة مباشرة
stats = mgr.get_all_stats()
print("=== Bots stats ===")
for name, s in stats.items():
    print(name, s)

# اطبع آخر أوامر
orders = mgr.get_all_orders()
print("\n=== Recent orders (top 10) ===")
for o in orders[:10]:
    print(o)
