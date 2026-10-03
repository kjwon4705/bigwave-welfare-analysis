"""275개 원문 조건 검토 기록과 관측가능성 감사. 자격 예측모델이 아니다.

정책별 판단은 검토명세.tsv에서 명시한다. 키워드로 자격이나 주체를 생성하지
않는다. 조건관계 요약을 완전한 실행식으로 가장하지 않으며 기존 제외를 유지한다.
"""
from pathlib import Path
import hashlib
import html
import json
import shutil
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '분석/Result/정책275_정밀검토_20261003'
DEST = ROOT / '분석/Processed_data/정책275_검토'
SITE = ROOT / '분석/Result/site'
MANIFEST = ROOT / 'Code/정책275_검토명세.tsv'
SOURCE = ROOT / '분석/Raw_data/중앙부처복지서비스_데이터_보완.csv'
RISK = ROOT / '분석/Result/공통변수_최종감사_20261003/전수위험점검461.csv'
SOURCE_HASH = '3133f57353d31c979033d797f3ac44a7a00b85a2d344143f4b4e83da28853b78'
RISK_HASH = '4ec5a11b6ba07a39397d80ae9ffcc219ae47a3afe330329426d0ca6c03c89372'

# 명세에 직접 기입한 대응항목. '관련 관측'은 정책요건 충족과 같지 않다.
OBS = {
 'A': ('연령', '만연령', '응답자 조사시점 만연령. 자녀·입소·전역 당시 나이와 월말생일은 알 수 없음.'),
 'G': ('성별', '성별코드', '응답자 성별. 임신·출산·자녀나 배우자의 성별은 알 수 없음.'),
 'N': ('현재 국적', '현재국적코드', '1 대한민국, 2 외국. 난민·귀화일·비자·특별기여자 여부는 미관측.'),
 'S': ('학교급·재학상태', '교육정도코드;재학상태코드', '학교급과 재학3/휴학4 관측. 학년·학교명·학교유형·전공·성적·휴학기간은 별도.'),
 'E': ('조사주간 경제활동·직업', '지난1주간경제활동여부;종사상지위코드;직장산업대분류코드', '활동1/비활동2, 임금근로1·자영업2/3. 법정실업·기업규모·보험·근속을 뜻하지 않음.'),
 'I': ('가구소득구간', '가구소득코드', '월가구소득 100만원 폭 구간, 최상위800만원이상. 개인·부부·연소득·소득인정액·건보료·학자금구간으로 변환 불가.'),
 'Hh': ('가구 규모·점유형태', '분류코드_가구원수;점유형태코드', '61=1인,62=2인,63=3인,64=4인이상. 완전한 자녀명부·법정세대·5인이상·무주택 소유조사 아님.'),
 'L': ('지역', '행정구역시도코드;분류코드_동부읍면부구분코드', '시도·동부3/읍면부4. 시군구·주소·법정농어촌/도서·거주기간·사업장소재지는 미관측.'),
 'Dobs': ('장애인복지카드 소유 응답', '장애인복지카드_소유여부', '1 소유,2 미소유. 장애유형·정도·적용법률 미관측; 미소유를 법정장애 없음으로 바꾸지 않음.'),
 'Fobs': ('가구주관계·혼인·일부 자녀 응답', '가구주관계코드;혼인상태코드;혼인신고여부;자녀유무', '개인 응답 간 관계는 참고 가능. 자녀문항은60세이상이며13세미만 자녀의 완전명부·친권·양육·법정한부모 자격은 알 수 없음.'),
}
MISSING = {
 'K': ('법정 급여·보호 자격', '기초생활 급여종류, 차상위 유형, 법정한부모, 의료급여종류, 타급여 자격·지급결정', '증명서·행정자격 확인 필요'),
 'D': ('장애 유형·정도·법정 판정', '등록장애, 장애유형, 중증/비중증, 산재·보훈·고용법 등 서로 다른 등급체계', '카드소유 응답은 관련정보이며 세부판정 대체 불가'),
 'F': ('가족·자녀·임신출산·양육', '완전한 자녀명부·월령, 친권·양육·입양·위탁, 부양관계, 배우자·부모 정보, 임신·출산일', '개인관계 응답만으로 법정가구 완성 불가; 자녀문항은60세이상'),
 'M': ('이주배경·체류·특별신분', '법정다문화, 탈북·납북피해, 난민·특별기여, 합법체류·국적취득/입국일', '현재 국적은 이 신분들과 다름'),
 'B': ('보훈·유족·수권', '보훈대상 법정유형·상이등급, 유족순위·권한·지정', '사회조사에 직접 자격 관측 없음'),
 'I': ('정책 기준 소득', '개인·부부 연소득/매출, 인정액, 건보료, 학자금지원구간, 보장가구별 산정값', '응답 가구소득 구간의 중간값 대입 금지'),
 'V': ('재산·주택·채무·신용', '전체세대 주택소유, 금융/일반재산·부채·차량, 신용점수·채권·임대계약', '월소득이나 점유형태로 대신할 수 없음'),
 'J': ('직역·사업장·경력·구직', '사업자/경영체등록, 기업유형·규모, 직업자격·근속·체불·구직활동·역할', '경제활동 관측보다 세부 정의가 필요'),
 'Sx': ('상세 학적·학업', '학교명·법정유형·사업참여, 학년·전공·성적·이수학점·유예·휴학기간·특수교육', '교육정도/재학코드만으로 판정 불가'),
 'C': ('의료·피해·필요성·의사', '진단·검사·주수·입원, 위기·피해, 돌봄/상담/교육 필요성, 취업·자립·이용 의사', '주관응답·활동제약으로 의료·행정 사실을 확정하지 않음'),
 'H': ('가입·이용·사건 이력', '보험가입·납부, 보호/퇴소/전역·등록·계약·이수, 과거지급·중복수혜', '횡단면 응답에서 기간·행정이력을 역추정하지 않음'),
 'T': ('정확한 기준시점·기간', '생년월일, 신청일·입소일·퇴소일, 경과일수, 과세/출생연도·적용시기', '2025년 조사값을2026년 신청현재로 간주하지 않음'),
 'L': ('세부 주소·사업지역', '시군구/도서·시설/사업장 주소, 거주기간·주민등록, 사업참여지역', '시도 및 동읍면구분은 충분한 대체자료 아님'),
 'U': ('요금·공급·이용 계약', '가스·전기·TV·난방 공급/계약, 전력량, 기기보유·요금유형', '가구주나 거주지역만으로 계약조건 판정 불가'),
 'O': ('기관·기업 자료', '법인/사업장 등록, 근로자수·장애고용률, 기관지정·위탁·사업계획', '개인설문과 분석단위가 다름'),
 'R': ('기관 판단·상세 공고', '위원회·의사·학교·금융기관 평가, 상세공고·지역별 기준·추천·배정', '질문 응답만으로 최종선정을 확정할 수 없음'),
}

# 원문을 읽고 정한 목록. 제목의 '운영'이나 '지원' 검색으로 만든 분류가 아니다.
ORGANISATION = {50,138,139,158,160,161,170,180,184,191,195,209,217,224,228,230,237,244,251,252,255}
GENERAL = {45,85}
SOURCE_ISSUES = {
 92: '12세 이하와2013년이후 출생,2025~26사업기간 등 기준시점 혼재. 백신별 현재 공고 필요.',
 94: '2단계·3단계 지역이 중복 기재되고 종료지역 포함. 현재 참여지역·단계 확인 필요.',
 114: '첫 소득경로에 3500만원 이거나라고 기재되어 이하 등 비교연산자가 빠져 있음.',
 122: '중위소득 기준과 최저생계비120/130% 등 과거 체계가 동시에 기재됨.',
 142: '구 장애1~3급·최저생계비130% 표현과 현행급여 설명 혼재. 적용기준 확인 필요.',
 146: '6세 이상과2019.12.31 출생경계의 기준연도 및 학령기 선정목록 역할 확인 필요.',
 155: '나열된 임대주택 유형 각각에60㎡조건이 적용되는지 본문만으로 명료하지 않음.',
 184: '상시 근로자 50일 미만이라고 기재되어 인원 단위 오류가 의심됨.',
 189: '지원대상은 교사, 선정기준은 학생 특수교육판정. 프로그램별 주체·절차 명료화 필요.',
 204: '선정기준에 저소득층 장애인을 지원과 소득무관이 함께 기재되어 필수/우선 관계 확인 필요.',
 261: '2024년 선발 학년·성적기준이 남아 있어 현재 적용연도 공고와 대조 필요.',
 266: '2026년 지원내용과2014년생 취학유예 사례가 함께 기재되어 출생연도 갱신 확인 필요.',
}
SOURCE_FOLLOWUPS = {
 94: ('국민건강보험공단 2026년 제도 안내', 'https://www.nhis.or.kr/renewal_popup/poster/20260204_poster_longdesc_1.html',
      '2단계는 안양·대구달서·용인·익산,3단계는 전주·원주·충주·홍성으로 확인. 원문 중복지역은 단계별로 분리한다. 전체 지역별 선정규칙 검증은 별도.'),
 114: ('서민금융진흥원 햇살론일반', 'https://www.kinfa.or.kr/financialProduct/hessalLoanGeneral.do',
       '연소득3500만원 이하는 신용점수와 무관한 경로이며,4500만원 이하 경로에는 신용하위20%가 함께 필요하다. 첫 경로의 누락된 이하를 공식 상품안내로 확인.'),
 184: ('근로복지공단 희망나무 대체인력지원금', 'https://webzine.comwel.or.kr/vol137/sub02.html',
       '공단 설명에서는 재해월말 상시근로자50인 미만으로 제시한다. 원문50일의 단위오류 보정 근거이며, 해당 자료만으로2026년 전체 요건을 확정하지 않는다.'),
 204: ('정부 2026 K-희망사다리 정책 안내', 'https://gonggam.korea.kr/gonggamWeb/publication/pdf/2026_K_ladder_of_hope.pdf',
       '2026 정부 정책안내는5~69세 장애인에 소득무관으로 설명한다. 저소득을 전체 필수요건으로 강제하지 않는다. 지방자치단체의 선정순위·등록증빙은 별도.'),
 266: ('찾기쉬운 생활법령정보 2026 보육사업안내 인용', 'https://easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=2&cciNo=3&cnpClsNo=1&csmSeq=626&popMenu=ov',
       '2026 일반보육 연령표의 취학유예 대상은2019년생으로 제시된다. 다문화보육은 어린이집 이용 조건도 필요하다. 원문2014년생 사례를2026년 확정조건으로 사용하지 않는다.'),
}

def split_codes(text):
    return [] if text == '-' else text.split(',')

def load_inputs():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_HASH, '원문 변경: 재검토 필요'
    assert hashlib.sha256(RISK.read_bytes()).hexdigest() == RISK_HASH, '검토대상 변경: 명세번호를 재연결해야 합니다.'
    p = pd.read_csv(SOURCE).fillna('')
    r = pd.read_csv(RISK).fillna('')
    ids = set(r.loc[r['재검토플래그수'].gt(0), '서비스ID'])
    target = p[p['서비스ID'].isin(ids)].copy().reset_index(drop=True)
    target.insert(0,'번호',range(1,len(target)+1))
    m = pd.read_csv(MANIFEST,sep='|').fillna('')
    assert len(target) == len(m) == 275 and m['번호'].tolist() == list(range(1,276))
    assert target['서비스ID'].is_unique and p['서비스ID'].is_unique
    return target, r, m

def eligibility_release(record, proposed_result):
    """검토요약/일반안내/부분 실행식을 실제 수급자격으로 유출하지 않는 게이트.

    현재 전275개는 완전 실행식·동일기준시점·완전관측 검증을 마치지 않았으므로
    True/False/None 중 어떠한 입력도 실제 자격으로 공개하지 않는다.
    """
    if record['주체분류'] == '기관·사업주 지원 경로 중심':
        return {'state':'분석단위 분리','eligible':None}
    gates = ['전체조건식검증완료','정책과관측기준시점일치','필수정보완전관측','원문정합성확인완료']
    if not all(record.get(k,False) for k in gates):
        return {'state':'미확인','eligible':None}
    if proposed_result not in (True,False,None):
        raise ValueError('허용되지 않는 판정값')
    return {'state':'미확인' if proposed_result is None else '조건부합' if proposed_result else '조건비해당', 'eligible':proposed_result}

def records_and_tables():
    target,risk,m = load_inputs()
    config=json.loads((ROOT/'Code/활성정책_설정.json').read_text(encoding='utf-8'))
    from 공통변수_v3 import rules_for
    existing=rules_for(pd.read_csv(SOURCE).fillna(''))
    old=pd.read_csv(ROOT/'분석/Archive/20261003_재분석이전/분석/Processed_data/중앙부처복지서비스_변수화.csv').fillna('').set_index('서비스ID')
    risk=risk.set_index('서비스ID')
    exclusions=set(config['audit_excluded'])|set(config['retired_model_policies'])
    records=[];mapping=[];evidence=[];changes=[];checks=[]
    for (_,p),(_,review) in zip(target.iterrows(),m.iterrows()):
        n=int(p['번호']);pid=p['서비스ID'];quote=review['근거구절']
        matches=[]
        for field in ['지원대상 상세','선정기준','지원내용 상세']:
            start=str(p[field]).find(quote)
            if start>=0:
                # 구절의 바로 앞뒤 문맥을 보존; 인용 앵커 자체는 명세에 직접 지정.
                context=str(p[field])[max(0,start-50):start+len(quote)+180]
                matches.append({'번호':n,'서비스ID':pid,'근거필드':field,'문자시작위치':start,'근거구절':quote,'원문문맥':context})
        assert matches,(n,quote)
        evidence.extend(matches)
        observed=split_codes(review['대응변수코드']);missing=split_codes(review['부족정보코드'])
        # 사람이 지정한 부족정보 범주에 대응하는 참고 관측도 누락하지 않는다.
        # 이것은 자격조건 추출이나 결측 대체가 아니다.
        if 'D' in missing:observed.append('Dobs')
        if 'F' in missing:observed.append('Fobs')
        assert all(k in OBS for k in observed) and all(k in MISSING for k in missing)
        assert missing or n in GENERAL
        group='일반안내 가능' if n in GENERAL else '기관·사업주 지원 경로 중심' if n in ORGANISATION else '추가정보·세부조건 확인 필요'
        rec={
          '번호':n,'서비스ID':pid,'서비스명':p['서비스명'],'소관부처':p['소관부처'],
          '대상주체':review['주체'],'주체분류':group,'조건관계요약':review['조건구조요약'],
          '정정및주의':review['정정및주의'],'관련관측코드':observed,'부족정보코드':missing,
          '원문확인사항':SOURCE_ISSUES.get(n,''),'원문기준연도':p['기준연도'],
          '공식자료보완요약':SOURCE_FOLLOWUPS[n][2] if n in SOURCE_FOLLOWUPS else '',
          '공식자료출처':SOURCE_FOLLOWUPS[n][0] if n in SOURCE_FOLLOWUPS else '',
          '공식자료URL':SOURCE_FOLLOWUPS[n][1] if n in SOURCE_FOLLOWUPS else '',
          '공식자료대조일':'2026-10-03' if n in SOURCE_FOLLOWUPS else '',
          '근거구절':quote,'근거필드':[x['근거필드'] for x in matches],
          '복지로링크':p['복지로 상세링크'],'원문지원대상':p['지원대상 상세'],
          '원문선정기준':p['선정기준'],'원문지원내용':p['지원내용 상세'],
          '원문요건검토':'보관 원문 대조·조건관계요약·관측가능성 검토',
          '실행식상태':'기존v3 부분실행식/안내식 있음' if pid in existing else '요약구조화; 완전 실행식 미작성',
          '전체조건식검증완료':False,'정책과관측기준시점일치':False,'필수정보완전관측':False,
          '원문정합성확인완료':False,'현재추천목록포함':pid in config['active_policy_ids'],
          '기존제외유지':pid in exclusions,'안내가능성_전국민일반안내':n in GENERAL,
          '실제자격검증완료':False,
        }
        # 부족정보 목록은 AND 조건식이 아니다. 한 경로의 미관측으로 모든 경로를 부정하지 않는다.
        rec['부족정보목록의미']='정책 내 하나 이상의 경로에서 필요한 확인항목 목록; 모든 항목의 AND 또는 모든 사람의 필수질문 목록 아님'
        rec['실제자격공개결과']=eligibility_release(rec,True)['state']
        records.append(rec)
        for k in observed:
            name,cols,limit=OBS[k]
            mapping.append({'번호':n,'서비스ID':pid,'서비스명':p['서비스명'],'종류':'관련 관측; 자격을 의미하지 않음','코드':k,'정보항목':name,'대응원변수':cols,'제약':limit})
        # 모든 정책에 공통인 설문-신청시점 차이를 항목 누락과 별개로 기록한다.
        for k in missing:
            name,need,limit=MISSING[k]
            mapping.append({'번호':n,'서비스ID':pid,'서비스명':p['서비스명'],'종류':'추가확인 항목','코드':k,'정보항목':name,'대응원변수':'직접충족 판정에 필요한 자료 부족','제약':need+' / '+limit})
        flags=[col for col in risk.columns if col not in ['서비스명','재검토플래그수','해석'] and risk.loc[pid,col] in [True,1,'True']]
        before={col:old.loc[pid,col] for col in ['최소연령','최대연령','연령필요','생애주기_청년','장애인','학생','자녀여부','취업여부','소득상한_중위소득%','수급자','차상위']}
        changes.append({'번호':n,'서비스ID':pid,'서비스명':p['서비스명'],'종전위험플래그':'; '.join(flags),
          '종전코딩값':json.dumps(before,ensure_ascii=False,default=str),'교정원칙':review['정정및주의'],
          '검토후조건구조':review['조건구조요약'],'변경적용범위':'검토카탈로그·실제자격 공개차단; 현행8개 외 자동재포함 없음'})
        results=[eligibility_release(rec,v) for v in [True,False,None]]
        checks.append({'번호':n,'서비스ID':pid,'서비스명':p['서비스명'],'원문근거대조':True,
          '코드정의대조':True,'불완전정보_자격유출차단':all(x['eligible'] is None for x in results),
          '기존제외정책재포함':False,'사람별전조건판정검증':'미완료; 검증게이트 시험과 별개'})
    return records,pd.DataFrame(mapping),pd.DataFrame(evidence),pd.DataFrame(changes),pd.DataFrame(checks)

def write_xlsx(tables,path):
    with pd.ExcelWriter(path,engine='openpyxl') as writer:
        for name,df in tables.items():
            df.to_excel(writer,sheet_name=name,index=False)
            ws=writer.book[name];ws.freeze_panes='C2';ws.auto_filter.ref=ws.dimensions
            for cell in ws[1]:
                cell.fill=PatternFill('solid',fgColor='244F73');cell.font=Font(name='맑은 고딕',bold=True,color='FFFFFF')
                cell.alignment=Alignment(wrap_text=True,vertical='top')
            for col in ws.columns:ws.column_dimensions[col[0].column_letter].width=18 if col[0].value in ['번호','서비스ID'] else 55
            for row in ws.iter_rows(min_row=2):
                for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
                ws.row_dimensions[row[0].row].height=78

def build():
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    records,mapping,evidence,changes,checks=records_and_tables()
    config=json.loads((ROOT/'Code/활성정책_설정.json').read_text(encoding='utf-8'))
    overview=pd.DataFrame([{
      '번호':r['번호'],'서비스ID':r['서비스ID'],'서비스명':r['서비스명'],'소관부처':r['소관부처'],
      '신청수혜주체':r['대상주체'],'검토분류':r['주체분류'],'조건관계요약':r['조건관계요약'],
      '사회조사관련관측':'; '.join(OBS[k][0] for k in r['관련관측코드']) or '직접대응 없음',
      '부족정보':'; '.join(MISSING[k][0] for k in r['부족정보코드']) or '일반안내 범위만 별도자격 없음',
      '정정및주의':r['정정및주의'],'원문확인사항':r['원문확인사항'],'실행식상태':r['실행식상태'],
      '공식자료보완요약':r['공식자료보완요약'],'공식자료출처':r['공식자료출처'],'공식자료URL':r['공식자료URL'],
      '원문기준연도':r['원문기준연도'],'현재추천목록포함':r['현재추천목록포함'],
      '근거구절':r['근거구절'],'복지로링크':r['복지로링크'],
      '검토범위':'수집된 원문의 조건 검토; 최신공고·완전실행식·실제선정 정답 검증은 아님',
    } for r in records])
    issues=overview[overview['원문확인사항'].ne('')].copy()
    freq=mapping[mapping['종류'].eq('추가확인 항목')].groupby('정보항목')['서비스ID'].nunique().sort_values(ascending=False).rename('정책수_중복허용').reset_index()
    summary={'review_date':'2026-10-03','original_policies':461,'flagged_reviewed':275,'outside_this_review':186,
      'review_class_counts':overview['검토분류'].value_counts().to_dict(),'source_clarification_needed':len(issues),
      'official_partial_crosschecks':len(SOURCE_FOLLOWUPS),
      'matched_evidence_policies':evidence['서비스ID'].nunique(),'availability_mapped_policies':275,
      'release_guard_tested_policies':len(checks),'legacy_diagnostic_rules_within_275':12,
      'new_complete_eligibility_rules':0,'actual_eligibility_validated':0,
      'active_policies_preserved':len(config['active_policy_ids']),'retired_policies_preserved':len(config['retired_model_policies']),
      'source_sha256':SOURCE_HASH,'review_manifest_sha256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
      'meaning':'275개 보관 원문의 조건 검토 완료. 완전한 자격 실행식 검증·최신공고 검증·모델학습 완료를 뜻하지 않음',
      'replay_meaning':'실제자격 공개차단 시험275건. 정책별 긍정/부정/경계 사례를 전부 검증한 수가 아님.'}
    meta={'summary':summary,'policies':records}
    replay=diagnostic_replay(records)
    summary['diagnostic_replay_count']=len(replay)
    summary['review_target_sha256']=RISK_HASH
    (DEST/'정책조건_검토카탈로그.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    tables={'정책275검토표':overview,'변수대응표':mapping,'원문근거':evidence,'종전코딩대조':changes,
      '원문확인필요12':issues,'부족정보집계':freq,'안전장치검증':checks,
      '기존12개진단재계산':replay,
      '원문보존':pd.DataFrame([{k:r[k] for k in ['번호','서비스ID','서비스명','원문기준연도','원문지원대상','원문선정기준','원문지원내용','복지로링크']} for r in records])}
    for name,df in tables.items():df.to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig')
    overview.to_csv(DEST/'정책275_검토표.csv',index=False,encoding='utf-8-sig')
    write_xlsx(tables,OUT/'정책275_검토결과.xlsx')
    write_report(overview,freq,summary)
    append_site()
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def diagnostic_replay(records):
    """기존 부분식이 있는12개만 실제설문으로 재계산. 미작성263개에 가짜 실행식을 만들지 않음."""
    import numpy as np
    from 공통변수_v3 import rules_for
    from 조건판정_v3 import make_facts,evaluate
    raw=pd.read_csv(next((ROOT/'분석/Raw_data').glob('2025_*.csv')),encoding='cp949',low_memory=False)
    facts=make_facts(raw);weights=facts['가구원가중값'];rules=rules_for(pd.read_csv(SOURCE).fillna(''))
    result=[]
    for r in records:
        pid=r['서비스ID']
        if pid not in rules:continue
        values=evaluate(rules[pid][0],facts)
        row={'번호':r['번호'],'서비스ID':pid,'서비스명':r['서비스명'],'표본수':len(facts),
          '해석':'조사시점 관측조건에 기존부분식을 적용한 진단.2026년 실제수급자격 판정 아님.',
          '실제자격공개':eligibility_release(r,True)['state']}
        for label,mask in [('관측조건부합',values==1),('관측조건비해당',values==0),('미확인',np.isnan(values))]:
            row[label+'_표본수']=int(mask.sum());row[label+'_가중%']=float(100*weights[mask].sum()/weights.sum())
        result.append(row)
    assert len(result)==12
    return pd.DataFrame(result)

def write_report(overview,freq,summary):
    counts=summary['review_class_counts']
    md=f'''# 정책275개 조건 검토 결과

수집 정책461개 중 기존 위험점검에서 표시된275개를 검토했다. 나머지186개는 이번 검토 범위 밖이며 안전 판정을 뜻하지 않는다.

|분류|정책수|
|---|---:|
|일반 정보·초기상담 안내 가능|{counts['일반안내 가능']}|
|기관·사업주 지원 경로가 중심|{counts['기관·사업주 지원 경로 중심']}|
|추가정보·세부조건 확인 필요|{counts['추가정보·세부조건 확인 필요']}|
|합계|275|

일반안내2개는 가족전용상담전화·마을변호사이며 지원금 수급자격이 확인된2개라는 의미가 아니다. 기관지원분류에는 개인 이용서비스가 함께 설명된 경우도 있다. 해당 이용경로는 분리해서 검토해야 한다. 추가확인252개는 질문만 하면 모두 판정할 수 있다는 뜻이 아니다.

## 수행 범위

1. 보관된 지원대상·선정기준을275개 모두 읽고, 필요한 경우 지원내용까지 대조했다. 정책별 근거구절·원문필드·문자위치와 원문 전문을 저장했다.
2. 신청·수혜 주체, 지원경로의 AND/OR, 제외·예외·우선순위·본인부담 기준을 정책별 요약으로 작성했다. 요약은 실행 가능한 완전한 논리식이 아니다.
3. 사회조사 원변수·코드북과 대조해 관련 관측과 부족정보를 분리했다. 부족정보 목록은 모든 사람에게 질문할 목록이나 AND 조건식이 아니다.
4. 전275개에 대해 근거·목록·변수대응 일관성 및 미검증 자격 공개차단을 시험했다. 기존v3 진단식과 겹치는12개는 별도 관측조건 재계산 대상으로 분리했다. 이는275개의 모든 긍정·부정·연령경계 사례 검증 완료를 뜻하지 않는다.

## 새로 확정하지 않은 사항

원문 내부 정합성 확인이 필요한12개는 별도 목록에 남겼다. 최신 사업공고를 모두 재수집한 검토가 아니며, 오류로 보이는 문구를 추정으로 수정하지 않았다. 원문확인12개는 위275개 분류 안에 포함된 중복 집계이다.

2025년 횡단면 응답을2026년 신청일의 소득·고용·나이로 간주할 수 없다. 설문시점 기준의 조건 비교와 현재 신청자격 판단을 분리해야 한다. 카드 미소유는 등록장애 없음이 아니며 가구소득구간은 소득인정액이 아니다. 교육정도는 최고학력 응답이므로 개별 학교·학년이나 법정 학적 범위를 완전히 재구성할 수 없다.

현재자료만으로 실제 수급자격 전체를 검증 완료한 정책은0개이다. 이번에 새로 승인한 완전 실행식도0개이다. 기존8개 관측조건·안내 분석, 그 안의 무질문 일반안내2개, 기존19개 모델정책 제외를 유지한다. 모델 재학습이나 활성정책 확대는 수행하지 않았다.

## 다음 검증을 위한 산출물

정책275_검토결과.xlsx에는 정책별 조건요약, 변수대응, 원문근거, 종전코딩값, 원문확인12개, 안전장치검증, 원문보존을 수록했다. 완전 실행식을 만들려면 각 지원경로의 필수요건을 개별 원자조건으로 확정하고, 현재 사업공고와 시점을 맞춘 뒤 정책별 양성·음성·경계·예외 사례를 검증해야 한다. 행정 실제선정 데이터가 없어 수급예측 정확도는 제시하지 않는다.
'''
    (OUT/'검토보고서.md').write_text(md,encoding='utf-8')
    e=html.escape
    cards=''.join(f'<div class="card"><strong>{v}</strong><span>{e(k)}</span></div>' for k,v in summary['review_class_counts'].items())
    rows=[]
    for _,r in overview.iterrows():
        rows.append(f'''<tr data-group="{e(r['검토분류'])}"><td>{r['번호']}</td><td><b>{e(r['서비스명'])}</b><br><small>{e(r['서비스ID'])}</small></td><td>{e(r['검토분류'])}</td><td>{e(r['조건관계요약'])}<details><summary>근거와 변수대응 보기</summary><p><b>주체:</b> {e(r['신청수혜주체'])}</p><p><b>관련 관측:</b> {e(r['사회조사관련관측'])}</p><p><b>부족정보:</b> {e(r['부족정보'])}</p><p><b>교정:</b> {e(r['정정및주의'])}</p><p><b>보관 원문 근거:</b> {e(r['근거구절'])}</p><p><b>원문 추가확인:</b> {e(r['원문확인사항']) or '별도 목록에 없음; 최신공고 검증 완료를 뜻하지 않음'}</p><p><b>실행식:</b> {e(r['실행식상태'])}</p></details></td></tr>''')
    issue_rows=overview[overview['원문확인사항'].ne('')][['서비스명','원문확인사항']].to_html(index=False,escape=True)
    followups='<h3>공식자료 후속 대조5개</h3><p>일부 문구의 보완 근거입니다. 각 정책의 모든 요건을 최신화하거나 수급자격을 검증 완료했다는 뜻은 아닙니다.</p><ul>'
    md+='\n## 공식자료 후속 대조5개\n\n일부 문구의 보완 근거이며 정책 전체의 최신화·자격검증은 아니다.\n\n'
    for n,(title,url,note) in SOURCE_FOLLOWUPS.items():
        name=overview.loc[overview['번호'].eq(n),'서비스명'].iloc[0]
        followups+=f'<li><b>{e(name)}</b>: {e(note)} <a href="{e(url)}">{e(title)}</a></li>'
        md+=f'- **{name}**: {note} [{title}]({url})\n'
    followups+='</ul>'
    issue_rows+=followups
    (OUT/'검토보고서.md').write_text(md,encoding='utf-8')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>정책275개 조건 검토</title><style>
body{font-family:'Malgun Gothic',sans-serif;color:#203548;background:#f4f7fa;margin:0;line-height:1.7}main{max-width:1240px;margin:auto;padding:32px}nav a{margin-right:18px}h1{font-size:30px}section{background:white;border:1px solid #dbe4ec;border-radius:10px;padding:24px;margin:22px 0}.cards{display:flex;gap:14px;flex-wrap:wrap}.card{flex:1;min-width:190px;background:#e8f0f8;padding:20px;border-radius:10px}.card strong{display:block;font-size:36px}.card span{display:block}.note{border-left:5px solid #d38b35;background:#fff7e8;padding:18px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:12px;border-bottom:1px solid #dde5ec;text-align:left;vertical-align:top}th{background:#e9f0f6}small{color:#51677a}details{margin-top:12px}summary{cursor:pointer;color:#16639a}input,select{font:inherit;padding:10px;border:1px solid #9db0c1;border-radius:6px;margin:8px 8px 12px 0;max-width:90%}.scroll{overflow-x:auto}a{color:#165d91}td:nth-child(2){min-width:160px}td:nth-child(4){min-width:260px}</style><main><nav><a href="index.html">처음</a><a href="preprocessing_fixes.html">전처리 수정 기록</a><a href="no_question_model.html">무질문 일반안내</a></nav><h1>정책275개 조건 검토</h1><p>461개 중 위험 신호가 있었던275개 · 보관 원문 기준 · 2026.10.03</p>'''
    page+=f'''<div class="cards">{cards}</div><p class="note"><b>275개 조건 검토는 완료했지만,275개 수급자격 판정을 검증 완료한 것은 아닙니다.</b><br>일반안내2개는 지원금이 아닌 정보·초기상담입니다. 추가확인252개에는 증빙·기관심사가 필요한 정책이 포함됩니다. 원문확인12개는 위 분류와 중복됩니다.</p>
<section><h2>무엇을 확인했나요?</h2><ol><li>275개 지원대상·선정기준 대조, 근거와 원문 보존</li><li>신청·수혜 주체 및 지원경로·제외·우선순위 구분</li><li>사회조사 관측항목과 미관측 요건의 대응표 작성</li><li>근거 일치·검토 누락·미검증 자격 공개차단 검증</li></ol><p>조건관계요약은 완전한 실행식이 아닙니다.275개 전체의 양성·음성·경계 사례 검증과 최신공고 확인은 아직 남아 있습니다. 기존v3 진단식과 겹치는12개는 별도 재계산표로 구분했습니다.</p><p>2025년 조사응답과2026년 신청시점은 다릅니다. 가구소득·장애카드·1인가구 같은 관측을 법정자격으로 바꾸지 않습니다. 미확인은 부적격이 아닙니다.</p><p><b>기존8개 분석과 그 안의2개 무질문 일반안내를 유지합니다. 새로 완전한 실제 수급자격을 확인한 정책은0개입니다.</b> 기존19개 모델정책은 재포함하지 않았습니다.</p>
<p><a href="tables/정책275_검토결과.xlsx">전체 검토표 내려받기 (Excel)</a> · <a href="tables/정책275검토표.csv">정책별 검토 CSV</a> · <a href="reproduce/review275/검토보고서.md">검토 보고서</a></p></section>
<section><h2>원문 추가확인12개</h2><p>아래는 최신법령상 오류가 확정된 목록이 아니라, 보관 원문을 실행식으로 바꾸기 전에 정합성을 확인해야 하는 목록입니다.</p><div class="scroll">{issue_rows}</div></section>
<section><h2>정책별 검토표</h2><label>검색 <input id="q" placeholder="정책명·필요정보·조건 검색"></label><label>분류 <select id="g"><option value="">전체</option>'''
    page+=''.join(f'<option>{e(k)}</option>' for k in summary['review_class_counts'])
    page+='</select></label><p id="count">275개</p><div class="scroll"><table id="policies"><thead><tr><th>번호</th><th>정책</th><th>분류</th><th>조건관계요약</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'
    page+='''<section><h2>해석 범위</h2><p>나머지186개는 이번275개 검토 범위 밖입니다. 위험 플래그가 없다는 이유로 검증된 정책으로 취급하지 않습니다. 부족정보는 경로별 필요정보를 모은 목록이며 모든 신청인에게 전부 요구할 조건이 아닙니다. 이 보고서에는 사회조사 개인별 기록이 없습니다.</p></section></main><script>
const q=document.querySelector('#q'),g=document.querySelector('#g');function filter(){let n=0;document.querySelectorAll('#policies tbody tr').forEach(r=>{const yes=r.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!g.value||r.dataset.group===g.value);r.hidden=!yes;n+=yes});document.querySelector('#count').textContent=n+'개 / 전체275개'}q.addEventListener('input',filter);g.addEventListener('change',filter);
</script></html>'''
    (OUT/'검토보고서.html').write_text(page,encoding='utf-8')

def append_site():
    if not (OUT/'검토보고서.html').exists():return
    shutil.copy2(OUT/'검토보고서.html',SITE/'policy_review_275.html')
    public=SITE/'reproduce/review275';public.mkdir(parents=True,exist_ok=True)
    for f in ['summary.json','검토보고서.md']:shutil.copy2(OUT/f,public/f)
    for f in ['정책275_검토결과.xlsx','정책275검토표.csv','원문확인필요12.csv','부족정보집계.csv','안전장치검증.csv']:
        shutil.copy2(OUT/f,SITE/'tables'/f)
    # 검토명세는 서비스ID와 원문해시가 고정된 원문순서를 사용한다. 개인자료는 복사하지 않는다.
    for name in ['정책275_정밀검토.py','정책275_검토명세.tsv','test_정책275_정밀검토.py']:
        src=ROOT/'Code'/name
        if src.exists():
            # 배포 허용확장자 내 CSV로 명세를 공개한다. 원래 구분자는 | 이다.
            dest=public/(name.replace('.tsv','.csv'))
            shutil.copy2(src,dest)
    shutil.copy2(ROOT/'Code/정책제외_재분석.py',SITE/'reproduce/policy_analysis.py')
    (public/'README.md').write_text('정책275개 조건 검토 재현자료. 개인자료는 포함하지 않습니다.\n\n정책275_검토명세.csv는 파이프(|) 구분자이며 재현 시 Code/정책275_검토명세.tsv로 저장합니다. 원문·기존 위험목록·v3 코드는 원래 작업폴더 구조가 필요합니다. 요약을 완전 실행식으로 사용하지 마세요.\n',encoding='utf-8')
    for page in SITE.glob('*.html'):
        if page.name=='policy_review_275.html':continue
        text=page.read_text(encoding='utf-8')
        if 'href="policy_review_275.html"' not in text:
            link='<p style="padding:12px;background:#edf3f8"><a href="policy_review_275.html">추가 검토: 정책275개 원문·변수 대응 결과</a> — 조건 검토 기록이며 실제 수급자격 확정 목록이 아닙니다.</p>'
            # 본문 컨테이너 내부 삽입. head나style 안에 삽입하지 않는다.
            import re
            text=re.sub(r'(<body[^>]*>)',lambda m:m.group(1)+link,text,count=1,flags=re.I)
            page.write_text(text,encoding='utf-8')

if __name__=='__main__':build()
