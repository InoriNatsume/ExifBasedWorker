import os
from PIL import Image

def compute_dhash(path, hash_size=8):
    """이미지 경로를 받아 dHash(int) 값을 반환"""
    try:
        # 1. 이미지 열기 및 흑백 변환
        with Image.open(path) as img:
            img = img.convert("L")
            # 2. 리사이즈 (9x8) - 앤티앨리어싱 적용
            img = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            
            diff = 0
            width = hash_size + 1
            bit_index = 0
            
            # 3. 픽셀 비교 및 비트 생성
            for row in range(hash_size):
                for col in range(hash_size):
                    # 왼쪽 픽셀보다 오른쪽 픽셀이 밝으면 1
                    if pixels[row * width + col] > pixels[row * width + col + 1]:
                        diff |= (1 << bit_index)
                    bit_index += 1
            
            return diff
    except Exception as e:
        print(f"[Error] 이미지 처리 실패: {e}")
        return None

def main():
    print("=" * 50)
    print("      이미지 유사도(dHash) 측정기")
    print("=" * 50)
    print(" 사용법: 이미지를 이 창으로 드래그 앤 드롭 하세요.")
    print(" 종료하려면 Ctrl+C를 누르세요.")
    print("-" * 50)

    while True:
        try:
            print("\n[첫 번째 이미지]를 드래그 하세요:")
            path1 = input(">> ").strip().strip('"').strip("'") # 윈도우 경로 따옴표 제거
            
            if not os.path.exists(path1):
                print("! 파일이 존재하지 않습니다. 다시 시도해주세요.")
                continue

            print("[두 번째 이미지]를 드래그 하세요:")
            path2 = input(">> ").strip().strip('"').strip("'")

            if not os.path.exists(path2):
                print("! 파일이 존재하지 않습니다. 다시 시도해주세요.")
                continue

            # 해시 계산
            hash1 = compute_dhash(path1)
            hash2 = compute_dhash(path2)

            if hash1 is None or hash2 is None:
                continue

            # 거리 계산 (XOR 후 1의 개수 세기)
            # 파이썬 3.10 이상에서는 .bit_count() 사용 가능
            # 하위 버전 호환을 위해 bin().count('1') 사용
            xor_val = hash1 ^ hash2
            distance = bin(xor_val).count('1')
            
            # 결과 출력
            print(f"\n--- 결과 분석 ---")
            print(f"이미지 1 해시: {hash1:016x}")
            print(f"이미지 2 해시: {hash2:016x}")
            print(f"★ 해밍 거리(차이값): {distance}")
            print("-" * 20)
            
            # 가이드
            if distance == 0:
                print("판정: [완벽히 동일] (완전 중복)")
            elif distance <= 5:
                print("판정: [매우 유사] (크기 변경, 포맷 변경, 미세한 노이즈)")
            elif distance <= 12:
                print("판정: [유사함] (표정 변화, 가벼운 복장 변경, 워터마크)")
            elif distance <= 20:
                print("판정: [약간 유사] (복장 전체 변경, 구도는 같음)")
            else:
                print("판정: [다름] (구도가 다르거나 다른 이미지)")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"\n오류 발생: {e}")

if __name__ == "__main__":
    main()