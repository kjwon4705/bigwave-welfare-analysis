# 공통변수 v3 재현

기존 정책/사회조사 원자료 및 활성정책 설정을 가진 로컬 프로젝트에서 실행합니다.
이 폴더의 조건판정_v3.py, 공통변수_v3.py, test_공통변수_v3.py를 Code 폴더에 같은 이름으로 복사합니다.
policy_analysis.py는 Code/정책제외_재분석.py, no_question_analysis.py는 Code/무질문모델.py로 배치합니다.
`python Code/정책제외_재분석.py`가 전처리,8개 분석,모델B,수정 보고서를 순서대로 생성합니다.
전처리만 하려면 `python Code/공통변수_v3.py`를 실행합니다.
원자료 배치는 기존 README.md와 no_question_README.md를 참고하세요. pandas,numpy,openpyxl,matplotlib이 필요합니다.
`python -m unittest discover -s Code -p test_공통변수_v3.py -v`로 검사합니다.
구조화16개는 전체자격 검증 완료를 뜻하지 않습니다.445개는 미검토 잠금이며 기존453개 제외는 유지합니다.
정책 원문 해시가 바뀌면 실행을 중단합니다. 개인 원자료는 공개 저장소에 없습니다.
