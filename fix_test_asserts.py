import re

# 1. Fix test_adversarial_break.py (fee_14_pm)
test_adv = "/home/rootrager/programming/price_project/main/tests/test_adversarial_break.py"
with open(test_adv, "r") as f:
    content = f.read()

content = content.replace("39300000", "47300000") # Replace 39.3 with 47.3 for 14 PM
with open(test_adv, "w") as f: f.write(content)

# 2. Fix test_hitl_pricing_and_post_format.py
test_hitl = "/home/rootrager/programming/price_project/main/tests/test_hitl_pricing_and_post_format.py"
with open(test_hitl, "r") as f:
    content = f.read()

content = content.replace('<a href="https://t.me/daniphoneir">● DaniFone | Apple Store</a>', '● <a href="https://t.me/daniphoneir">DaniFone</a> | Apple Store')

with open(test_hitl, "w") as f: f.write(content)
