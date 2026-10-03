"""원문근거·275개검토범위·자료대응·자격유출 차단 검사. 실제 수급정답 검증 아님."""
import json
import unittest
import pandas as pd
import 정책275_정밀검토 as m

class Review275Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records,cls.mapping,cls.evidence,cls.changes,cls.checks=m.records_and_tables()
        cls.by_n={r['번호']:r for r in cls.records}

    def test_exact_coverage_and_evidence(self):
        target,risk,_=m.load_inputs()
        ids=set(risk.loc[risk['재검토플래그수'].gt(0),'서비스ID'])
        self.assertEqual({r['서비스ID'] for r in self.records},ids)
        self.assertEqual(len(self.records),275)
        self.assertEqual(set(self.evidence['서비스ID']),ids)
        for _,r in self.evidence.iterrows():
            p=target[target['서비스ID'].eq(r['서비스ID'])].iloc[0]
            start=int(r['문자시작위치']);quote=r['근거구절']
            self.assertEqual(p[r['근거필드']][start:start+len(quote)],quote)

    def test_observed_columns_exist_and_do_not_claim_legal_status(self):
        file=next((m.ROOT/'분석/Raw_data').glob('2025_*.csv'))
        cols=set(pd.read_csv(file,encoding='cp949',nrows=0).columns)
        for name,fields,limitation in m.OBS.values():
            self.assertTrue(set(fields.split(';'))<=cols,name)
            self.assertTrue(limitation)
        self.assertEqual(len(self.mapping['서비스ID'].unique()),273) # 일반안내2개는 조건 대응 불필요
        for r in self.records:
            self.assertFalse(r['전체조건식검증완료'])

    def test_incomplete_rules_cannot_publish_true_or_false(self):
        for r in self.records:
            for proposal in [True,False,None]:
                with self.subTest(policy=r['서비스ID'],proposal=proposal):
                    self.assertIsNone(m.eligibility_release(r,proposal)['eligible'])
        # 알려진 일부조건 부합과 실제자격 공개는 별개이며, 안내정책에도 동일.
        self.assertTrue(self.by_n[45]['안내가능성_전국민일반안내'])
        self.assertIsNone(m.eligibility_release(self.by_n[45],True)['eligible'])

    def test_source_conflicts_never_promote(self):
        self.assertEqual(len(m.SOURCE_ISSUES),12)
        for n in m.SOURCE_ISSUES:
            self.assertTrue(self.by_n[n]['원문확인사항'])
            self.assertFalse(self.by_n[n]['원문정합성확인완료'])

    def test_existing_exclusions_and_units(self):
        c=json.loads((m.ROOT/'Code/활성정책_설정.json').read_text(encoding='utf-8'))
        self.assertEqual(len(c['active_policy_ids']),8)
        self.assertEqual(len(c['retired_model_policies']),19)
        for r in self.records:
            if r['기존제외유지']:self.assertFalse(r['현재추천목록포함'])
        self.assertEqual(len(m.ORGANISATION),21)
        # '운영'이라는 제목만으로 개인서비스를 기관전용으로 분류하면 안 된다.
        self.assertNotIn(67,m.ORGANISATION)
        self.assertNotIn(141,m.ORGANISATION)
        self.assertIn(139,m.ORGANISATION)

    def test_summary_is_not_full_eligibility(self):
        s=json.loads((m.OUT/'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(s['review_class_counts'].values()),275)
        self.assertEqual(s['review_class_counts']['추가정보·세부조건 확인 필요'],252)
        self.assertEqual(s['new_complete_eligibility_rules'],0)
        self.assertEqual(s['actual_eligibility_validated'],0)

    def test_replay_keeps_unknown_in_denominator(self):
        x=pd.read_csv(m.OUT/'기존12개진단재계산.csv')
        self.assertEqual(len(x),12)
        self.assertTrue(x['표본수'].eq(33944).all())
        self.assertTrue(x[['관측조건부합_표본수','관측조건비해당_표본수','미확인_표본수']].sum(axis=1).eq(33944).all())
        self.assertTrue((x.filter(regex='가중%$').sum(axis=1)-100).abs().lt(1e-8).all())
        self.assertTrue(x['실제자격공개'].eq('미확인').all())

if __name__=='__main__':unittest.main()
