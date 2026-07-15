import os
import sys
import time
import random
import msvcrt

highest_score = 0

# ==================== 游戏主循环（无限把） ====================
while True:
    os.system('cls')

    # === 1. 显示乘法口诀表 ===
    print("=" * 58)
    print(" " * 20 + "📖  乘法口诀表")
    print("=" * 58)
    for i in range(1, 10):
        for j in range(1, i + 1):
            print(f"{j}×{i}={i * j:2d}", end="  ")
        print()
    print("=" * 58)
    print("\n  准备好了！倒计时即将开始...")
    time.sleep(2)

    # === 2. 初始化本局 ===
    score = 5
    start_time = time.time()

    # === 3. 出题循环（60秒倒计时） ===
    while True:
        os.system('cls')

        # 检查倒计时
        remaining = 60 - (time.time() - start_time)
        if remaining <= 0:
            break  # 时间到，跳出出题循环

        # ========== 顶部倒计时 UI（窗口上方正中） ==========
        bar_len = int(remaining / 2)  # 进度条长度
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print()
        print(" " * 25 + "┌──────────────────────────────┐")
        print(" " * 25 + f"│       ⏱  剩余 {int(remaining):02d} 秒        │")
        print(" " * 25 + f"│  [{bar}]  │")
        print(" " * 25 + f"│        得分：{score} 分           │")
        print(" " * 25 + "└──────────────────────────────┘")
        print()
        # 分数爱心条
        heart_str = "❤️" * score + "🖤" * (5 - score)
        print(" " * 25 + heart_str)
        print()
        print("=" * 58)

        # === 4. 随机出题 ===
        a = random.randint(1, 9)
        b = random.randint(1, a)
        print(f"\n{' ' * 22}{a}  ×  {b}  =  ?")
        print(f"{' ' * 20}(输入答案后按回车，按 q 退出)")
        print()

        # === 5. 倒计时输入（msvcrt 非阻塞） ===
        print(" " * 25 + "答案：", end="", flush=True)
        user_input = ""
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b'\r':  # 回车
                    break
                elif ch == b'q':
                    print("\n\n  再见！")
                    sys.exit(0)
                elif b'0' <= ch <= b'9':
                    user_input += ch.decode()
                    print(ch.decode(), end="", flush=True)
                elif ch == b'\b' or ch == b'\x7f':  # 退格
                    if user_input:
                        user_input = user_input[:-1]
                        print("\b \b", end="", flush=True)
            else:
                # 倒计时检查
                if time.time() - start_time >= 60:
                    user_input = "__timeout__"
                    break
                time.sleep(0.05)

        if user_input == "__timeout__":
            break

        # === 6. 判分 ===
        correct_answer = a * b
        print()  # 换行
        time.sleep(0.2)

        if user_input.isdigit() and int(user_input) == correct_answer:
            score += 1
            print(f"\n{' ' * 25}✅  正确！+1分  （{score}分）")
        else:
            score -= 1
            print(f"\n{' ' * 25}❌  错误！{a}×{b}={correct_answer}，-1分  （{score}分）")
        time.sleep(0.8)

        # === 7. 检查是否扣到 0 分 ===
        if score <= 0:
            os.system('cls')
            # 屏幕中央巨大的红色 "你输了"
            print("\n" * 4)
            print(" " * 18 + "\033[91m╔══════════════════════════════════╗\033[0m")
            print(" " * 18 + "\033[91m║                                ║\033[0m")
            print(" " * 18 + "\033[91m║      你  输  了  ！！          ║\033[0m")
            print(" " * 18 + "\033[91m║                                ║\033[0m")
            print(" " * 18 + "\033[91m╚══════════════════════════════════╝\033[0m")
            print("\n" * 4)
            time.sleep(3)
            break

    # === 8. 本局结束 - 统计得分 ===
    os.system('cls')
    print("\n" * 3)
    print(" " * 25 + "📊  本局统计")
    print("=" * 58)
    print(f"\n{' ' * 25}本局得分：{score} 分")

    # 更新最高分
    if score > highest_score:
        highest_score = score
        print(f"{' ' * 25}🏆  新纪录！最高分：{highest_score}")
    else:
        print(f"{' ' * 25}历史最高分：{highest_score}")

    print()
    print("=" * 58)
    print(f"\n{' ' * 20}按任意键开始下一把...")

    # 等待按键
    while not msvcrt.kbhit():
        time.sleep(0.1)
    msvcrt.getch()
