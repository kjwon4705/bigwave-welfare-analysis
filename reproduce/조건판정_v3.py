"""정책 조건과 사람 사실을 구분하는 3값 판정 엔진. 미추출/미관측은 미확인."""
import numpy as np
import pandas as pd

VERSION='3.0.0'


def and3(*values):
    if not values:raise ValueError('빈 AND를 무조건 충족으로 해석할 수 없습니다.')
    a=np.vstack(values).astype(float)
    return np.where((a==0).any(axis=0),0.,np.where(np.isnan(a).any(axis=0),np.nan,1.))


def or3(*values):
    if not values:raise ValueError('빈 OR를 판정할 수 없습니다.')
    a=np.vstack(values).astype(float)
    return np.where((a==1).any(axis=0),1.,np.where(np.isnan(a).any(axis=0),np.nan,0.))


def not3(value):return 1.-np.asarray(value,dtype=float)


def atom(field,op,value=None,subject='applicant',role='required',note=''):
    return dict(field=field,op=op,value=value,subject=subject,role=role,note=note)


def all_of(*args):return {'all':list(args)}
def any_of(*args):return {'any':list(args)}
def unknown(reason):return {'unknown':reason}


def evaluate(expr,facts):
    """정책을 '미관측'으로 생성한 경우 명시 unknown 사용. 결측/주체불일치를 false로 바꾸지 않음."""
    n=len(facts)
    operators=[k for k in ('all','any','not','unknown','constant','field') if k in expr]
    if len(operators)!=1:raise ValueError('조건 노드는 하나의 연산만 가져야 합니다.')
    k=operators[0]
    if k in ('all','any'):
        children=[evaluate(x,facts) for x in expr[k]]
        return (and3 if k=='all' else or3)(*children)
    if k=='not':return not3(evaluate(expr[k],facts))
    if k=='unknown':return np.full(n,np.nan)
    if k=='constant':
        if expr[k] not in [0,1]:raise ValueError('상수는0/1만 허용')
        return np.full(n,float(expr[k]))
    field=expr['field'];op=expr['op']
    if op not in ['eq','positive_evidence','in','between','gte','lt','gte18_month','under18_month']:
        raise ValueError('지원하지 않는 연산자: '+op)
    # 신청인의 나이를 자녀나 배우자의 나이 대신 사용하지 않는다.
    if expr.get('subject','applicant')!='applicant' or field not in facts:
        return np.full(n,np.nan)
    v=facts[field];present=v.notna();target=expr.get('value')
    if op=='eq':result=v.eq(target)
    elif op=='positive_evidence':
        result=v.eq(target);present=present&result
    elif op=='in':result=v.isin(target)
    elif op=='between':result=v.between(*target)
    elif op=='gte':result=v.ge(target)
    elif op=='lt':result=v.lt(target)
    elif op=='gte18_month':
        result=v.ge(18);present=present&v.ne(17) # 월말에18세가 되는 예외를 만연령만으로 판정하지 않음
    else:
        result=v.lt(18);present=present&v.ne(17)
    return np.where(present,result.astype(float),np.nan)


def observed_flag(series,yes,valid):
    return pd.Series(np.where(series.isin(valid),series.isin(yes).astype(float),np.nan),index=series.index)


def make_facts(raw):
    """행단위 관측사실만 생성. 법정 자격/소득인정액/가구주관계의 역추정 금지."""
    keys=['가구일련번호','가구원번호']
    if raw.duplicated(keys).any():raise ValueError('사람 키 중복')
    f=raw[keys+['가구원가중값','가구가중값']].copy()
    f['만연령']=raw['만연령'];f['성별코드']=raw['성별코드']
    f['현재국적코드']=raw['현재국적코드'].where(raw['현재국적코드'].isin([1,2]))
    f['복지카드소유_관측']=observed_flag(raw['장애인복지카드_소유여부'],[1],[1,2])
    f['동읍면구분']=raw['분류코드_동부읍면부구분코드'].map({3:'동부',4:'읍면부'})
    f['행정구역시도코드']=raw['행정구역시도코드']
    f['가구원수_하한']=raw['분류코드_가구원수'].map({61:1,62:2,63:3,64:4})
    f['가구원수_상한']=raw['분류코드_가구원수'].map({61:1,62:2,63:3})
    f['가구원수_상한상태']=np.where(raw['분류코드_가구원수'].eq(64),'4인이상_상한미공개',np.where(f['가구원수_하한'].notna(),'정확값','미관측'))
    f['1인가구_관측']=observed_flag(raw['분류코드_가구원수'],[61],[61,62,63,64])
    # 가구 문항은 응답 충돌이 없을 때만 전파한다. max로 상충값을 선택하지 않는다.
    for col in ['가구소득코드','점유형태코드']:
        if raw.groupby('가구일련번호')[col].nunique().gt(1).any():raise ValueError('가구내 상충응답: '+col)
        f[col]=raw.groupby('가구일련번호')[col].transform('first')
    income=f['가구소득코드'];f['월가구소득_하한원']=income.map({i:(i-1)*1_000_000 for i in range(1,10)})
    f['월가구소득_상한원']=income.map({i:i*1_000_000 for i in range(1,9)})
    f['월가구소득_상한상태']=np.where(income.eq(9),'상한없음',np.where(income.isin(range(1,9)),'상한미포함','미관측'))
    f['소득개념']='조사 응답 월가구소득구간; 소득인정액 아님'
    f['생활비_정부사회단체지원_관측']=observed_flag(raw['생활비마련방법코드'],[3],[1,2,3,4])
    f['자녀유무_60세이상응답']=observed_flag(raw['자녀유무'],[1],[1,2]).where(raw['만연령'].ge(60))
    f['자녀문항_관측상태']=np.where(raw['만연령'].lt(60),'조사대상밖',np.where(f['자녀유무_60세이상응답'].notna(),'관측','미응답'))
    f['교육정도코드']=raw['교육정도코드'].where(raw['교육정도코드'].isin(range(8)))
    f['재학상태코드']=raw['재학상태코드'].where(raw['재학상태코드'].isin(range(1,6)))
    edu=f['교육정도코드'];enr=f['재학상태코드']
    school=observed_flag(edu,[1,2,3],range(8))
    f['초중고재학_관측']=and3(school,observed_flag(enr,[3],range(1,6)))
    f['초중고재학휴학_관측']=and3(school,observed_flag(enr,[3,4],range(1,6)))
    f['재학휴학_관측']=observed_flag(enr,[3,4],range(1,6));f.loc[edu.eq(0),'재학휴학_관측']=0.
    f['지난주경제활동_관측']=observed_flag(raw['지난1주간경제활동여부'],[1],[1,2])
    status=raw['종사상지위코드']
    f['임금근로_관측']=and3(f['지난주경제활동_관측'],observed_flag(status,[1],[1,2,3,4]))
    f['자영업_관측']=and3(f['지난주경제활동_관측'],observed_flag(status,[2,3],[1,2,3,4]))
    f['농림어업산업_관측']=and3(f['지난주경제활동_관측'],observed_flag(raw['직장산업대분류코드'],['A'],list('ABCDEFGHIJKLMNOPQRSTU')))
    f['군인직업_관측']=observed_flag(raw['직업대분류코드'].astype('string'),['A'],list('123456789A'))
    f['생애주기_집계용']=pd.cut(raw['만연령'],[-1,5,12,18,34,64,np.inf],labels=['영유아','아동','청소년','청년','중장년','노년'])
    # 자격을0으로 추정하지 않는다. 직접 수집하지 않은 법정/특수 사실은명시적 결측.
    for name in ['기초생활수급자_법정','의료급여수급권_법정','차상위_법정','등록장애_법정','장애중증_법정','소득인정액','한부모_법정','조손_법정','다문화_법정','무주택_법정','질병진단','구직실업_법정']:
        f[name]=np.nan
    f['생성버전']=VERSION
    return f


def curated_rules():
    age=lambda op,v=None:atom('만연령',op,v)
    legal=atom('등록장애_법정','eq',1)
    benefits=any_of(atom('기초생활수급자_법정','eq',1),atom('차상위_법정','eq',1))
    pending=lambda detail:unknown(detail)
    adult=age('gte18_month')
    student18_20=all_of(age('between',[18,20]),atom('초중고재학휴학_관측','eq',1))
    return {
     'WLF00006295':({'constant':1},'일반안내','별도 지원요건 없는 일반 원격상담 안내. 현장방문·실제 이용은 대상 밖.'),
     'WLF00006315':({'constant':1},'일반안내','별도 선정기준 없는 일반 가족 정보·초기상담 안내. 심화 연계는 대상 밖.'),
     'WLF00003265':(all_of(adult,legal,atom('장애중증_법정','eq',0),benefits,{'not':student18_20},pending('신청기준일·장애정도·소득인정액 및 예외 검토 필요')),'부분구조화','장애수당:18세 이상 AND 등록장애 AND 비중증 AND(수급OR차상위),18~20세 재학/휴학 제외.20세는 전체 상한 아님.'),
     'WLF00003198':(all_of(any_of(age('under18_month'),all_of(age('between',[18,20]),atom('초중고재학휴학_관측','eq',1),pending('장애인연금 비수급·학교범위·생일 예외'))),legal,benefits,pending('신청월 기준·행정 자격 확인')),'부분구조화','18세 미만 기본경로 OR18~20세 학생 예외경로. 본인 수혜자 기준, 자녀보유 필수 아님.'),
     'WLF00003249':(all_of(adult,legal,atom('장애중증_법정','eq',1),pending('본인·배우자의 소득인정액과 재산'),pending('직역연금 제외 및 재포함 예외')),'부분구조화','장애인연금:자녀보유/기초생활수급을 필수로 만들지 않음. 본인·배우자 소득·직역연금 별도.'),
     'WLF00006229':(all_of(age('lt',75),pending('공무원·사학 교직원·졸업예정/잔여수학기간·자영업매출·기업규모 및 소득 등 제외조건')),'부분구조화','국민내일배움카드:75세 미만. 학생/자영업 자체를 필수 또는 일괄 제외로 만들지 않음.'),
     'WLF00003263':(all_of(atom('초중고재학_관측','eq',1),pending('상담·교육활동 필요성')),'부분구조화','학생 본인의 초중고재학 AND 상담 필요. 부모의 자녀보유와 생애주기태그를 사용하지 않음.'),
     'WLF00004650':(pending('아동청소년·교사·양육자 등 프로그램별 대상과 이용범위'),'부분구조화','청소년 태그만으로 성인 교사·양육자를 제외하지 않음. 프로그램 범위 미확정.'),
     'WLF00006318':(all_of(age('between',[18,39]),atom('IQ','between',[71,84]),pending('보관 원문 외 신청절차·검사 증빙 완전성 미검증')),'부분구조화','신청인18~39세 AND IQ71~84. IQ를 등록장애로 대체하지 않음.'),
     'WLF00001083':(all_of(atom('현재국적코드','positive_evidence',1),pending('AI·디지털에 어려움을 겪는 상태')),'부분구조화','국적만으로 통과하지 않음. 외국국적 경로는 명시되지 않아 별도 원문검토 필요.'),
     'WLF00000056':(all_of(atom('의료급여수급권_법정','eq',1),any_of(*[pending(x) for x in ['질병·부상·출산 요양','자동복막투석','당뇨 소모품·관리기기','자가도뇨','산소치료','인공호흡기·기침유발기','양압기']]),pending('의료급여 수급권 종류·처방·구입 및 이용증빙')),'부분구조화','여러 의료급여 요양 경로. 정책 전체에 여성/임신/19~49세를 강제하지 않음.'),
     'WLF00006308':(all_of(atom('현재국적코드','positive_evidence',1),pending('법률상담 필요성')),'부분구조화','법률상담 필요성을 국민 여부로 대체하지 않음.'),
     'WLF00000031':(atom('현재국적코드','positive_evidence',1),'일반안내_일부관측','한국 국적자에 한해 일반안내 가능. 외국국적은미확인. 실제 선정 판정은 대상 밖.'),
     'WLF00000066':(all_of(legal,pending('정보화교육 필요성')),'부분구조화','카드 미소유를 등록장애 없음으로 바꾸지 않음. 교육 필요성은미관측.'),
    }
