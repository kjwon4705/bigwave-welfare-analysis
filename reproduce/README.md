# 재현 방법
개인 원자료는 공개하지 않습니다. pandas, numpy, matplotlib, openpyxl이 필요합니다.

로컬 프로젝트에 다음 파일을 배치합니다.
- policy_analysis.py → Code/정책제외_재분석.py
- active_config.json → Code/활성정책_설정.json
- 보관 정책 원문 → 분석/Raw_data/중앙부처복지서비스_데이터_보완.csv
- 이용 허가를 받은 사회조사 원자료 → 분석/Raw_data/2025_*.csv (한 파일)

분석/Processed_data 및 발표자료/중간보고회발표자료/그림 폴더를 만든 뒤 프로젝트 루트에서 Python으로 Code/정책제외_재분석.py를 실행합니다.
정책 원문 해시가 보관본과 다르면 중단합니다. 개인 원자료가 없는 공개 저장소만으로는 다시 계산할 수 없습니다.
가중치는 가구원가중값을 사용하고 unknown은 비율 분모에 포함합니다. 공개 설정은 정책ID 목록이며 개인ID가 아닙니다.
