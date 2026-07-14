import re

def validate_password(password):
    """
    비밀번호 검증 함수
    조건: 영문 소문자, 영문 대문자, 숫자, 기호(특수문자) 각각 최소 1개 이상 포함
    """
    # 각 조건을 개별 정규표현식으로 검사
    has_lower = re.search(r'[a-z]', password)
    has_upper = re.search(r'[A-Z]', password)
    has_digit = re.search(r'\d', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/;\'~`]', password)

    errors = []
    if not has_lower:
        errors.append("영문 소문자가 최소 1개 이상 필요합니다.")
    if not has_upper:
        errors.append("영문 대문자가 최소 1개 이상 필요합니다.")
    if not has_digit:
        errors.append("숫자가 최소 1개 이상 필요합니다.")
    if not has_special:
        errors.append("특수문자(기호)가 최소 1개 이상 필요합니다.")

    if errors:
        return False, errors
    return True, ["모든 조건을 만족합니다."]


def main():
    print("비밀번호 검증 프로그램 (종료하려면 '!!!' 입력)")
    print("-" * 50)

    while True:
        password = input("비밀번호를 입력하세요: ")

        if password == "!!!":
            print("프로그램을 종료합니다.")
            break

        is_valid, messages = validate_password(password)

        print()
        if is_valid:
            print("✅ 유효한 비밀번호입니다!")
        else:
            print("❌ 유효하지 않은 비밀번호입니다:")
            for msg in messages:
                print(f"  - {msg}")
        print("-" * 50)


if __name__ == "__main__":
    main()