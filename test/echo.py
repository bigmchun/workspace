def main():
    print("문장을 입력하세요 (종료하려면 '!!!' 입력)")
    print("-" * 40)

    while True:
        user_input = input(">> ")

        # 종료 조건 체크
        if user_input == "!!!":
            print("프로그램을 종료합니다. 안녕히 가세요!")
            break

        print("입력하신 문장은:", user_input)


if __name__ == "__main__":
    main()