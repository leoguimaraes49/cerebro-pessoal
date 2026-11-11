import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from nucleo import Conflict
from pathlib import Path
from nucleo import Store,REAL_SYSTEM,Invalid
from conhecimento import Knowledge
from apoio_decisao import prepare

class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');p=Path(self.tmp.name)
        self.s=Store(p/'sistema',p/'cofre');self.k=Knowledge(self.s)
        source=self.s.apply('f','create',title='Relato fictício',text='Posso estudar de manhã ou à tarde.')
        self.refs=[{'record_id':source['id'],'revision':1}]
        self.options=[{'descricao':'Manhã','origem':'relatada_pelo_usuario','pros':['Tempo disponível'],'contras':[],'incertezas':['Qualidade do sono']},
                      {'descricao':'Tarde','origem':'sugerida_pela_ia','pros':[],'contras':[],'incertezas':['Compromissos']}]
    def tearDown(self):self.tmp.cleanup()
    def test_choice_not_made_suggestions_not_attributed_to_user(self):
        r=prepare(self.k,'d','Horário fictício','Escolher horário',self.options,self.refs,['Quais compromissos existem?'])
        self.assertEqual(r['choice'],'not_made');self.assertFalse(r['external_actions'])
        payload=self.k.read(r['decision']['id'])['record']['payload']
        self.assertEqual(payload['perceived_options'],['Manhã']);self.assertEqual(payload['decision_status'],'considering')
        self.assertEqual(len(r['questions']),1)
    def test_repeat_does_not_duplicate(self):
        a=prepare(self.k,'d','Horário fictício','Escolher horário',self.options,self.refs,[])
        b=prepare(self.k,'d','Horário fictício','Escolher horário',self.options,self.refs,[])
        self.assertEqual(a,b)
    def test_no_invented_perceived_options(self):
        for item in self.options:item['origem']='sugerida_pela_ia'
        with self.assertRaises(Invalid):prepare(self.k,'d','Fictício','Escolher',self.options,self.refs,[])
    def test_changed_context_suspends_analysis(self):
        r=prepare(self.k,'d','Horário fictício','Escolher horário',self.options,self.refs,[])
        self.s.apply('corrige','correct',ident=self.refs[0]['record_id'],expected=1,text='Não posso pela manhã',reason='Correção fictícia')
        self.assertEqual(self.k.read(r['analysis']['id'])['validity'],'needs_revalidation')
    def test_stale_source_not_accepted(self):
        self.refs[0]['revision']=99
        with self.assertRaises(Invalid):prepare(self.k,'d','Fictício','Escolher',self.options,self.refs,[])
    def test_partial_failure_reports_confirmed_effect(self):
        original=self.k.apply
        def apply(*args,**kwargs):
            if args[1]=='synthesis':raise Conflict('falha fictícia na análise')
            return original(*args,**kwargs)
        with patch.object(self.k,'apply',apply):
            result=prepare(self.k,'d','Fictício','Escolher',self.options,self.refs,[])
        self.assertEqual(result['status'],'partial');self.assertEqual(len(result['confirmed_effects']),1)
        self.assertEqual(result['choice'],'not_made')

    def test_sqlite_failure_preserves_confirmed_decision_and_retry(self):
        original=self.k.apply
        def interrupted(*args,**kwargs):
            if args[1]=='synthesis':raise sqlite3.OperationalError('database is locked - fixture')
            return original(*args,**kwargs)
        with patch.object(self.k,'apply',interrupted):
            result=prepare(self.k,'sql','Fictício','Escolher',self.options,self.refs,[])
        self.assertEqual(result['status'],'partial');self.assertEqual(len(result['confirmed_effects']),1)
        self.assertEqual(result['choice'],'not_made');self.assertFalse(result['external_actions'])
        resumed=prepare(self.k,'sql','Fictício','Escolher',self.options,self.refs,[])
        self.assertEqual(resumed['status'],'confirmed')
        self.assertEqual(resumed['decision'],result['confirmed_effects'][0])


if __name__=='__main__':unittest.main(verbosity=2)
