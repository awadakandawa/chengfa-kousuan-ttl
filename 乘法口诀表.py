import random

# 打印 9x9 乘法口诀表
for i in range(1, 10):
    for j in range(1, i + 1):
        print(f"{j}×{i}={i*j:2d}", end="  ")
    print()

# 收集所有乘法算式
questions = []
for i in range(1, 10):
    for j in range(1, i + 1):
        questions.append((j, i, i * j))

# 随机抽一道题
a, b, correct = random.choice(questions)
answer = int(input(f"\n来，算一道：{a}×{b} = "))

if answer == correct:
    print("哎呦我去，你真是天才")
else:
    print(f"傻孩子，这都能错？正确答案是 {correct}")
