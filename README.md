# 사진 커서 (PhotoCursor)

Windows 컴퓨터 전체의 마우스 커서를 내 사진으로 바꾸고, 클릭하는 순간 잠깐 다른 사진으로 바뀌게 하는 프로그램이에요.
Python 같은 프로그램을 따로 설치하지 않아도 돼요.

## 받기

**[PhotoCursor.zip 내려받기](../../releases/latest/download/PhotoCursor.zip)**

압축을 풀면 이런 파일이 들어 있어요.

| 파일 | 무엇인가 |
|---|---|
| `PhotoCursor.exe` | 프로그램 본체. 더블클릭하면 켜져요. |
| `settings.txt` | 크기, 불투명도, 클릭 기준점 같은 설정. 메모장으로 열어서 바꿔요. |
| `normal.png` | 평소 커서 사진 (예시) |
| `click.png` | 클릭할 때 사진 (예시) |

## 쓰는 법

1. 압축을 푼 폴더에 내 사진을 넣어요. 이름을 아래처럼 맞추면 돼요. 투명 배경 PNG가 가장 자연스러워요.
   - `normal.png`: 평소 (화살표 커서 자리)
   - `click.png`: 클릭하는 순간 (어디서 클릭하든)
   - `text.png`: 글자 입력칸 위 (I자 커서 자리). 없으면 Windows 원래 커서
   - `link.png`: 링크·버튼 위 (손가락 커서 자리). 없으면 Windows 원래 커서
2. `PhotoCursor.exe`를 더블클릭해요.
3. 끄려면 **Ctrl + Alt + Q**. 또는 `PhotoCursor.exe`를 한 번 더 실행하고 "예"를 눌러요.

### 처음 실행할 때 파란 경고창이 뜨면

"Windows의 PC 보호" 창이 뜰 수 있어요. 이 exe는 돈을 내고 받는 '코드 서명'이 없어서 Windows가 처음 보는 프로그램으로 여기기 때문이에요.
**추가 정보 → 실행**을 누르면 돼요. 이 exe는 이 저장소의 `photo_cursor.py` 코드로 GitHub가 직접 만든 거예요 ([만든 기록](../../actions)).

## 설정 바꾸기

`settings.txt`를 메모장으로 열고 `=` 오른쪽 값만 바꾼 뒤 저장해요. 끄고 다시 켜야 적용돼요.
각 설정이 무엇인지는 파일 안에 설명이 같이 적혀 있어요.

## 원래 커서로 안 돌아올 때

프로그램이 갑자기 꺼지면 사진 커서가 남을 수 있어요. 이럴 때는 아래 중 하나를 하면 돼요.

- `PhotoCursor.exe`를 다시 켰다가 Ctrl + Alt + Q로 끄기
- 컴퓨터 다시 시작하기 (다시 켜면 항상 원래 커서로 돌아와요)

## 컴퓨터 켤 때 자동으로 켜기 (선택)

Win + R → `shell:startup` 입력 → 열린 폴더에 `PhotoCursor.exe`의 **바로 가기**를 넣어요.
(exe 자체를 옮기면 사진과 설정 파일을 못 찾아요. 꼭 바로 가기로 넣으세요.)

## 만든 방식

`photo_cursor.py` 하나가 전부예요. `main` 브랜치에 코드를 올리면 GitHub Actions가 Windows에서 exe를 만들고, 커서 바꾸기가 되는지 점검한 뒤 Releases에 올려요 (`.github/workflows/build.yml`).
