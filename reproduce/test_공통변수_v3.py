import itertools
import json
import unittest
import numpy as np
import pandas as pd
from 조건판정_v3 import make_facts,evaluate,and3,or3,not3,atom,all_of,unknown
from 공통변수_v3 import load,rules_for,schema_for,DEST,ROOT


class FixedConditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config,cls.policies,cls.raw,_=load()
        cls.rules=rules_for(cls.policies)
        cls.byname=cls.policies.set_index('서비스명')['서비스ID']

    def score(self,name,**values):
        return evaluate(self.rules[self.byname[name]][0],pd.DataFrame([values]))[0]

    def test_three_value_all_cases(self):
        for a,b in itertools.product([0.,1.,np.nan],repeat=2):
            want_and=0 if a==0 or b==0 else (np.nan if np.isnan(a) or np.isnan(b) else 1)
            want_or=1 if a==1 or b==1 else (np.nan if np.isnan(a) or np.isnan(b) else 0)
            np.testing.assert_equal(and3([a],[b])[0],want_and)
            np.testing.assert_equal(or3([a],[b])[0],want_or)
        with self.assertRaises(ValueError):and3()
        with self.assertRaises(ValueError):evaluate({'all':[]},pd.DataFrame(index=[0]))
        self.assertTrue(np.isnan(not3([np.nan])[0]))

    def test_age_exceptions_no_wrong_bounds(self):
        self.assertTrue(np.isnan(self.score('장애수당',만연령=40,초중고재학휴학_관측=0)))
        self.assertEqual(self.score('장애수당',만연령=16),0)
        self.assertEqual(self.score('장애수당',만연령=19,초중고재학휴학_관측=1),0)
        self.assertTrue(np.isnan(self.score('장애수당',만연령=17)))
        self.assertTrue(np.isnan(self.score('장애아동수당',만연령=14)))
        self.assertTrue(np.isnan(self.score('장애아동수당',만연령=19,초중고재학휴학_관측=1)))
        self.assertEqual(self.score('장애아동수당',만연령=30),0)

    def test_exclusion_subject_and_missing_essential_facts(self):
        self.assertEqual(self.score('마을변호사',만연령=16),1)
        self.assertTrue(np.isnan(self.score('국민내일배움카드제 직업훈련지원(훈련비, 훈련장려금)',만연령=30,재학휴학_관측=0,자영업_관측=0)))
        self.assertTrue(np.isnan(self.score('WEE 클래스 상담지원',만연령=16,초중고재학_관측=1,자녀유무_60세이상응답=0)))
        self.assertEqual(self.score('WEE 클래스 상담지원',초중고재학_관측=0),0)
        self.assertTrue(np.isnan(self.score('경계선지능청년지원 사업',만연령=30)))
        self.assertEqual(self.score('경계선지능청년지원 사업',만연령=30,IQ=90),0)
        self.assertTrue(np.isnan(self.score('디지털배움터',현재국적코드=1)))
        self.assertTrue(np.isnan(self.score('의료급여(요양비)',만연령=70,성별코드=1)))
        self.assertTrue(np.isnan(self.score('장애인연금',만연령=40,자녀유무_60세이상응답=0,기초생활수급자_법정=0)))

    def test_employment_routes(self):
        self.assertEqual(self.score('직장인 든든한 점심밥',임금근로_관측=0,지난주경제활동_관측=1,자영업_관측=1),0)
        self.assertTrue(np.isnan(self.score('체불 근로자 생계비 융자',임금근로_관측=0,지난주경제활동_관측=0)))

    def test_unknown_subject_and_legal_status(self):
        f=pd.DataFrame({'만연령':[30]})
        self.assertTrue(np.isnan(evaluate(atom('만연령','gte',18,subject='child'),f)[0]))
        x=make_facts(self.raw)
        for col in ['기초생활수급자_법정','차상위_법정','등록장애_법정','소득인정액','다문화_법정','무주택_법정']:
            if col in x:self.assertTrue(x[col].isna().all(),col)
        self.assertTrue(x.loc[self.raw['분류코드_가구원수'].eq(64),'가구원수_상한'].isna().all())
        self.assertTrue(x.loc[x['가구소득코드'].eq(9),'월가구소득_상한원'].isna().all())
        self.assertEqual(x['동읍면구분'].eq('읍면부').sum(),9118)
        self.assertTrue(x.loc[x['만연령'].lt(60),'자녀유무_60세이상응답'].isna().all())
        self.assertTrue(x.loc[self.raw['교육정도코드'].eq(0),'재학휴학_관측'].eq(0).all())
        self.assertNotIn('중위소득%_근사',x)

    def test_household_conflict_fails_and_empty_category_unknown(self):
        x=self.raw.iloc[:2].copy();x['가구일련번호']=999999;x['가구원번호']=[1,2];x['가구소득코드']=[1,2]
        with self.assertRaises(ValueError):make_facts(x)
        x=self.raw.iloc[[0]].copy();x['지난1주간경제활동여부']=np.nan;x['종사상지위코드']=np.nan
        f=make_facts(x);self.assertTrue(np.isnan(f['임금근로_관측'].iloc[0]))

    def test_locked_policies_and_no_resurrection(self):
        records=schema_for(self.policies,self.config)
        self.assertEqual(len(records),461)
        self.assertEqual(sum(x['검토상태']=='미검토_잠금' for x in records),445)
        self.assertFalse(any(x['전체자격검증완료'] for x in records))
        self.assertEqual(sum(x['기존제외유지'] for x in records),453)
        for x in records:
            if x['검토상태']=='미검토_잠금':self.assertTrue(np.isnan(evaluate(x['조건식'],pd.DataFrame(index=[0]))[0]))
        self.assertTrue(all(not x['현재추천목록포함'] for x in records if x['기존제외유지']))


if __name__=='__main__':unittest.main()
