"""SA UniGoiás 3.0. Python 3.10+, biblioteca padrão, SQLite."""
import argparse, datetime as dt, hashlib, hmac, http.cookies, json, math, os, re, secrets, shutil, sqlite3, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('SA_DB', BASE / 'data' / 'academico.sqlite3'))
TABLES = ('users','classes','students','subjects','offerings','enrollments','assessments','grades','lessons','attendance','materials','interventions')
FIELDS = {
 'users':'username name email role active', 'classes':'name level shift active',
 'students':'user_id cpf registration birth_date active', 'subjects':'name code hours active',
 'offerings':'subject_id class_id teacher_id period weekday start_time end_time room active',
 'enrollments':'student_id offering_id active', 'assessments':'offering_id title type date weight',
 'grades':'enrollment_id assessment_id value', 'lessons':'offering_id date start_time topic',
 'attendance':'enrollment_id lesson_id status', 'materials':'offering_id title url description trigger',
 'interventions':'enrollment_id owner_id action due_date status result'}
ATTEMPTS = {}; LOCK = threading.Lock()
class Problem(Exception):
 def __init__(self, message, status=400): self.message, self.status = message, status

def connect():
 c=sqlite3.connect(DB_PATH, timeout=15); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def hash_password(p):
 salt=secrets.token_hex(16)
 return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),260000).hex()
def verify(p, hashed):
 salt,digest=hashed.split(':')
 return hmac.compare_digest(digest,hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),260000).hex())
def password_policy(p):
 if not isinstance(p,str) or len(p)<10 or len(p)>128: raise Problem('A senha deve ter de 10 a 128 caracteres.')
def rows(c,t): return [dict(r) for r in c.execute('SELECT * FROM '+t)]
def get(c,t,i):
 r=c.execute('SELECT * FROM '+t+' WHERE id=?',(i,)).fetchone()
 if not r: raise Problem('Registro não encontrado: '+t,404)
 return dict(r)
def audit(c,u,action,entity,record=None,details=''):
 c.execute('INSERT INTO audit(actor_id,created_at,action,entity,record_id,details) VALUES(?,?,?,?,?,?)',(u,dt.datetime.now(dt.timezone.utc).isoformat(),action,entity,record,details))
def valid_date(s, future=False):
 if not isinstance(s,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',s):raise Problem('Informe uma data no formato AAAA-MM-DD.')
 try: d=dt.date.fromisoformat(s)
 except (ValueError,TypeError): raise Problem('Informe uma data válida.')
 if not future and d>dt.date.today(): raise Problem('A data não pode ser futura.')
def cpf_valid(s):
 if len(s)!=11 or len(set(s))==1:return False
 for n in (9,10):
  v=(sum(int(s[i])*(n+1-i) for i in range(n))*10)%11
  if int(s[n])!=(0 if v==10 else v):return False
 return True

def init_db(demo=False):
 DB_PATH.parent.mkdir(parents=True,exist_ok=True)
 with connect() as c:
  c.executescript((BASE/'schema.sql').read_text())
  if c.execute('SELECT count(*) FROM users').fetchone()[0]:return
  initial=os.environ.get('SA_ADMIN_PASSWORD')
  if not demo and not initial: raise SystemExit('Base vazia. Use --demo para dados fictícios ou defina SA_ADMIN_PASSWORD (10+ caracteres).')
  password_policy(initial or 'Demo@2026!')
  def ins(t,**v):return c.execute('INSERT INTO '+t+' ('+','.join(v)+') VALUES ('+','.join('?' for _ in v)+')',list(v.values())).lastrowid
  ins('users',username='admin',name='Administrador',email='admin@example.com',role='admin',password_hash=hash_password(initial or 'Demo@2026!'))
  if not demo:return
  for username,name,role in [('coord','Coordenação Acadêmica','coordinator'),('prof','Professor Silva','teacher'),('manuel','Manuel Silva','student'),('ana','Ana Costa','student'),('lucas','Lucas Almeida','student')]:
   ins('users',username=username,name=name,email=username+'@example.com',role=role,password_hash=hash_password('Demo@2026!'))
  ins('classes',name='Engenharia de Software • 6º período',level='Ensino superior',shift='Noturno')
  ins('classes',name='Engenharia de Software • 4º período',level='Ensino superior',shift='Noturno')
  for uid,cpf in [(4,'52998224725'),(5,'11144477735'),(6,'12345678909')]:ins('students',user_id=uid,cpf=cpf,registration='2026000'+str(uid-3),birth_date='2005-01-15')
  today=dt.date.today(); period=str(today.year)+'.2'
  for sid,(name,code,day) in enumerate([('Teste de Software','TST001',1),('Banco de Dados','BDD001',2),('Projeto Integrador III','PIN003',4)],1):
   ins('subjects',name=name,code=code,hours=60)
   ins('offerings',subject_id=sid,class_id=1,teacher_id=3,period=period,weekday=day,start_time='19:00',end_time='20:40',room='Lab '+str(sid))
   a1=ins('assessments',offering_id=sid,title='Trabalho aplicado',type='Trabalho',date=str(today-dt.timedelta(days=7)),weight=4)
   a2=ins('assessments',offering_id=sid,title='Prova do módulo',type='Prova Bimestral',date=str(today-dt.timedelta(days=2)),weight=6)
   ls=[ins('lessons',offering_id=sid,date=str(today-dt.timedelta(days=k)),start_time='19:00',topic='Aula '+str(5-k)) for k in (4,3,2,1)]
   for st in (1,2,3):
    en=ins('enrollments',student_id=st,offering_id=sid)
    ins('grades',enrollment_id=en,assessment_id=a1,value={1:5,2:9,3:7}[st]);ins('grades',enrollment_id=en,assessment_id=a2,value={1:4,2:8.5,3:7.5}[st])
    for j,l in enumerate(ls):ins('attendance',enrollment_id=en,lesson_id=l,status='Ausente' if st==1 and j<2 else 'Presente')
   ins('materials',offering_id=sid,title='Plano de revisão orientada',url='',description='Revise as atividades corrigidas; registre três dúvidas e leve-as à próxima orientação com o professor.',trigger='Nota baixa')
  ins('interventions',enrollment_id=1,owner_id=3,action='Agendar orientação e revisar o trabalho aplicado.',due_date=str(today+dt.timedelta(days=7)),status='Aberta',result='')
  audit(c,1,'SEED','database',details='Dados fictícios de demonstração criados.')

def permitted_offerings(c,u):
 if u['role'] in ('admin','coordinator'): return {r['id'] for r in c.execute('SELECT id FROM offerings')}
 if u['role']=='teacher':return {r['id'] for r in c.execute('SELECT id FROM offerings WHERE teacher_id=?',(u['id'],))}
 return {r[0] for r in c.execute('SELECT e.offering_id FROM enrollments e JOIN students s ON s.id=e.student_id WHERE s.user_id=?',(u['id'],))}
def offering_for(c,t,v):
 if t=='offerings':return v['id']
 if 'offering_id' in v:return int(v['offering_id'])
 if 'enrollment_id' in v:return get(c,'enrollments',v['enrollment_id'])['offering_id']
 return None

def authorize(c,u,t,v=None):
 role=u['role']
 if role=='student':raise Problem('Seu perfil permite somente consulta.',403)
 if t=='users' and role!='admin':raise Problem('Somente o administrador gerencia usuários.',403)
 if role=='teacher':
  if t not in ('assessments','grades','lessons','attendance','materials','interventions'):raise Problem('Operação restrita à gestão.',403)
  if v is not None and offering_for(c,t,v) not in permitted_offerings(c,u):raise Problem('Você não é responsável por esta oferta.',403)

def validate(c,t,v,old=None):
 for k in FIELDS[t].split():
  if k not in v:raise Problem('Campo obrigatório ausente: '+k)
  if isinstance(v[k],str):v[k]=v[k].strip()
  if v[k]=='' and k not in ('birth_date','url','result'):raise Problem('Preencha o campo '+k+'.')
  if isinstance(v[k],str) and len(v[k])>3000:raise Problem('Texto muito longo: '+k)
 for k in v:
  if k.endswith('_id') or k in ('hours','weekday','active'):
   try:
    if isinstance(v[k],bool) or str(v[k])!=str(int(v[k])):raise ValueError()
    v[k]=int(v[k])
   except (ValueError,TypeError):raise Problem('Valor inteiro inválido: '+k)
 if 'active' in v and v['active'] not in (0,1):raise Problem('Estado inválido.')
 if t=='users':
  v['username']=v['username'].lower()
  if not re.fullmatch(r'[a-z0-9_.-]{3,40}',v['username']):raise Problem('Usuário: 3 a 40 letras minúsculas, números, ponto, hífen ou sublinhado.')
  if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v['email']):raise Problem('E-mail inválido.')
  if v['role'] not in ('admin','coordinator','teacher','student'):raise Problem('Perfil inválido.')
  if old and old['role']!=v['role']:
   if c.execute('SELECT 1 FROM students WHERE user_id=?',(old['id'],)).fetchone() or c.execute('SELECT 1 FROM offerings WHERE teacher_id=?',(old['id'],)).fetchone() or c.execute('SELECT 1 FROM interventions WHERE owner_id=?',(old['id'],)).fetchone():raise Problem('Perfil vinculado a histórico; não pode ser alterado.')
  if old and old['role']=='admin' and (v['role']!='admin' or not v['active']):
   if c.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1 AND id<>?",(old['id'],)).fetchone()[0]==0:raise Problem('Mantenha pelo menos um administrador ativo.')
 if t=='students':
  v['cpf']=re.sub(r'\D','',v['cpf'])
  if not cpf_valid(v['cpf']):raise Problem('CPF inválido (verifique os dígitos).')
  user=get(c,'users',v['user_id'])
  if user['role']!='student' or not user['active']:raise Problem('Selecione um usuário aluno ativo.')
  if v['birth_date']:valid_date(v['birth_date'])
  else:v['birth_date']=None
 if t=='offerings':
  for key,table in [('subject_id','subjects'),('class_id','classes'),('teacher_id','users')]:
   r=get(c,table,v[key])
   if not r['active']:raise Problem('O vínculo exige um cadastro ativo.')
  if get(c,'users',v['teacher_id'])['role']!='teacher':raise Problem('O responsável deve ter perfil professor.')
  if not re.fullmatch(r'\d{4}\.[12]',v['period']):raise Problem('Período deve seguir AAAA.1 ou AAAA.2.')
  for key in ('start_time','end_time'):
   if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',v[key]):raise Problem('Horário inválido.')
  if v['active'] and c.execute('SELECT 1 FROM offerings WHERE active=1 AND period=? AND weekday=? AND id<>? AND start_time<? AND end_time>? AND (class_id=? OR teacher_id=? OR room=?)',(v['period'],v['weekday'],old['id'] if old else -1,v['end_time'],v['start_time'],v['class_id'],v['teacher_id'],v['room'])).fetchone():raise Problem('Conflito de horário da turma, professor ou sala.')
 if t=='enrollments':
  for k,tab in [('student_id','students'),('offering_id','offerings')]:
   if not get(c,tab,v[k])['active']:raise Problem('Matrícula exige aluno e oferta ativos.')
 if t in ('assessments','lessons','materials'):
  if not get(c,'offerings',v['offering_id'])['active']:raise Problem('Oferta inativa.')
 if t in ('grades','attendance','interventions'):
  en=get(c,'enrollments',v['enrollment_id'])
  if not en['active'] or not get(c,'students',en['student_id'])['active'] or not get(c,'offerings',en['offering_id'])['active']:raise Problem('Aluno, matrícula ou oferta inativa.')
  if t!='interventions':
   ref=get(c,'assessments' if t=='grades' else 'lessons',v['assessment_id' if t=='grades' else 'lesson_id'])
   if ref['offering_id']!=en['offering_id']:raise Problem('O lançamento e a matrícula devem pertencer à mesma oferta.')
   valid_date(ref['date'])
 if t=='interventions':
  valid_date(v['due_date'],True)
  owner=get(c,'users',v['owner_id'])
  if not owner['active'] or owner['role'] not in ('teacher','coordinator','admin'):raise Problem('Responsável inválido.')
  if owner['role']=='teacher' and get(c,'offerings',en['offering_id'])['teacher_id']!=owner['id']:raise Problem('Professor responsável deve ministrar esta oferta.')
  if v['status']=='Concluída' and not v['result']:raise Problem('Descreva o resultado antes de concluir.')
 if t=='assessments':valid_date(v['date'],True)
 if t=='lessons':
  valid_date(v['date'])
  if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',v['start_time']):raise Problem('Horário inválido.')
 if t=='materials' and v['url'] and not re.fullmatch(r'https?://[^\s]+',v['url']):raise Problem('O link deve começar com http:// ou https://.')
 for key in ('value','weight'):
  if key in v:
   try:v[key]=float(v[key]);assert math.isfinite(v[key])
   except (ValueError,TypeError,AssertionError):raise Problem('Número inválido.')
 # Chaves de histórico são imutáveis; correções de notas/presenças continuam permitidas.
 immutable={'students':['user_id'],'enrollments':['student_id','offering_id'],'offerings':['subject_id','class_id','period'],'assessments':['offering_id'],'lessons':['offering_id'],'grades':['enrollment_id','assessment_id'],'attendance':['enrollment_id','lesson_id']}
 if old:
  for key in immutable.get(t,[]):
   if old[key]!=v[key]:raise Problem('Vínculo não pode ser trocado. Crie um novo registro: '+key)

def mutate(c,u,t,p,method,i=None):
 if t not in TABLES:raise Problem('Recurso inexistente.',404)
 old=get(c,t,i) if i else None
 authorize(c,u,t,old)
 if method=='DELETE':
  if t=='users':raise Problem('Usuários devem ser inativados para preservar a auditoria.')
  c.execute('DELETE FROM '+t+' WHERE id=?',(i,));audit(c,u['id'],'DELETE',t,i,'Registro removido');return {'ok':True}
 v={k:p.get(k) for k in FIELDS[t].split() if k in p}
 validate(c,t,v,old);authorize(c,u,t,dict(v,id=i) if i else v)
 if t=='users':
  if i==u['id'] and (not v['active'] or v['role']!=u['role']):raise Problem('Não altere o próprio perfil ou estado durante a sessão.')
  pw=p.get('password','')
  if not old or pw:password_policy(pw);v['password_hash']=hash_password(pw)
 if old:
  c.execute('UPDATE '+t+' SET '+','.join(k+'=?' for k in v)+' WHERE id=?',list(v.values())+[i])
  if t=='users':c.execute('DELETE FROM sessions WHERE user_id=?',(i,))
 else:i=c.execute('INSERT INTO '+t+' ('+','.join(v)+') VALUES ('+','.join('?' for _ in v)+')',list(v.values())).lastrowid
 detail='Campos: '+', '.join(k for k in v if k!='password_hash')
 if t in ('grades','attendance'):detail=json.dumps({'antes':{k:old[k] for k in v} if old else None,'depois':v},ensure_ascii=False)
 audit(c,u['id'],'UPDATE' if old else 'CREATE',t,i,detail)
 return {'ok':True,'id':i}

def state(c,u):
 data={t:rows(c,t) for t in TABLES}; allowed=permitted_offerings(c,u)
 if u['role'] not in ('admin','coordinator'):
  data['offerings']=[x for x in data['offerings'] if x['id'] in allowed]
  data['enrollments']=[x for x in data['enrollments'] if x['offering_id'] in allowed]
  if u['role']=='student':
   mine={x['id'] for x in data['students'] if x['user_id']==u['id']}
   data['enrollments']=[x for x in data['enrollments'] if x['student_id'] in mine]
  ens={x['id'] for x in data['enrollments']}; sts={x['student_id'] for x in data['enrollments']}
  data['students']=[x for x in data['students'] if x['id'] in sts or x['user_id']==u['id']]
  for t in ('grades','attendance','interventions'):data[t]=[x for x in data[t] if x['enrollment_id'] in ens]
  for t in ('assessments','lessons','materials'):data[t]=[x for x in data[t] if x['offering_id'] in allowed]
  data['classes']=[x for x in data['classes'] if x['id'] in {o['class_id'] for o in data['offerings']}]
  data['subjects']=[x for x in data['subjects'] if x['id'] in {o['subject_id'] for o in data['offerings']}]
  visible={u['id']}|{x['user_id'] for x in data['students']}|{x['teacher_id'] for x in data['offerings']}|{x['owner_id'] for x in data['interventions']}
  data['users']=[x for x in data['users'] if x['id'] in visible]
  if u['role']=='teacher':
   for x in data['students']:x.pop('cpf',None);x.pop('birth_date',None)
 for x in data['users']:
  x.pop('password_hash',None)
  if u['role']=='student' and x['id']!=u['id']:x.pop('email',None);x.pop('username',None)
 data['settings']=dict(c.execute('SELECT * FROM settings').fetchone())
 data['audit']=[dict(r) for r in c.execute('SELECT a.*,u.name actor FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 500')] if u['role']=='admin' else []
 data['metrics']=metrics(data);return data

def metrics(d):
 result=[]; amin=d['settings']['min_grade']; fmin=d['settings']['min_attendance']
 for en in d['enrollments']:
  gs=[g for g in d['grades'] if g['enrollment_id']==en['id']]; fs=[f for f in d['attendance'] if f['enrollment_id']==en['id']]
  weights={a['id']:a['weight'] for a in d['assessments']}; total=sum(weights[g['assessment_id']] for g in gs)
  avg=sum(g['value']*weights[g['assessment_id']] for g in gs)/total if total else None
  frequency=100*sum(f['status']=='Presente' for f in fs)/len(fs) if fs else None
  pending=sum(a['offering_id']==en['offering_id'] for a in d['assessments'])-len(gs)
  reasons=[]
  if avg is not None and avg<amin:reasons.append('Nota baixa')
  if frequency is not None and frequency<fmin:reasons.append('Baixa frequência')
  result.append(dict(enrollment_id=en['id'],student_id=en['student_id'],offering_id=en['offering_id'],average=avg,frequency=frequency,assessed=len(gs),attendance_count=len(fs),pending=pending,reasons=reasons,active=en['active']))
 return result

def backup():
 target=BASE/'backups';target.mkdir(exist_ok=True)
 name=target/('academico-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.sqlite3')
 with connect() as src,sqlite3.connect(name) as dst:src.backup(dst)
 with sqlite3.connect(name) as dst:dst.execute('DELETE FROM sessions')
 return name

def backup_loop():
 while True:
  try:backup()
  except Exception as e:print('Falha no backup:',e,flush=True)
  time.sleep(86400)

class Handler(BaseHTTPRequestHandler):
 server_version='SAUniGoias/3.0'
 def reply(self,status,payload,headers=None):
  raw=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode();self.send_response(status)
  self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(raw)
 def body(self):
  try:n=int(self.headers.get('Content-Length',0))
  except ValueError:raise Problem('Tamanho inválido.')
  if n>100000 or n<0:raise Problem('Requisição muito grande.',413)
  try:
   v=json.loads(self.rfile.read(n) or '{}',parse_constant=lambda _:None)
   if not isinstance(v,dict):raise ValueError()
   return v
  except (ValueError,UnicodeDecodeError):raise Problem('JSON inválido.')
 def session(self,c):
  cookie=http.cookies.SimpleCookie();cookie.load(self.headers.get('Cookie',''))
  token=cookie['sa_session'].value if 'sa_session' in cookie else ''
  hashed=hashlib.sha256(token.encode()).hexdigest()
  s=c.execute('SELECT s.*,u.role,u.name,u.active FROM sessions s JOIN users u ON u.id=s.user_id WHERE token_hash=? AND expires>?',(hashed,time.time())).fetchone()
  if not s or not s['active']:raise Problem('Entre para continuar.',401)
  u=get(c,'users',s['user_id']);u.pop('password_hash');return u,dict(s)
 def do_GET(self):self.dispatch('GET')
 def do_POST(self):self.dispatch('POST')
 def do_PUT(self):self.dispatch('PUT')
 def do_DELETE(self):self.dispatch('DELETE')
 def dispatch(self,method):
  try:
   path=urlparse(self.path).path
   if not path.startswith('/api/'):
    if method!='GET':raise Problem('Método inválido.',405)
    return self.static(path)
   with connect() as c:
    if method!='GET':
     origin=self.headers.get('Origin')
     if origin and urlparse(origin).netloc!=self.headers.get('Host'):raise Problem('Origem não permitida.',403)
    if path=='/api/login' and method=='POST':
     p=self.body();key=self.client_address[0];now=time.time()
     with LOCK:
      ATTEMPTS[key]=[x for x in ATTEMPTS.get(key,[]) if now-x<300]
      if len(ATTEMPTS[key])>=10:raise Problem('Muitas tentativas. Aguarde cinco minutos.',429)
      ATTEMPTS[key].append(now)
     username=p.get('username','');pw=p.get('password','')
     if not isinstance(username,str) or not isinstance(pw,str):raise Problem('Credenciais inválidas.',401)
     r=c.execute('SELECT * FROM users WHERE username=? AND active=1',(username.strip(),)).fetchone()
     if not r or not verify(pw,r['password_hash']):raise Problem('Usuário ou senha inválidos.',401)
     with LOCK:ATTEMPTS.pop(key,None)
     token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
     c.execute('DELETE FROM sessions WHERE expires<?',(now,))
     c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),r['id'],csrf,now+28800));audit(c,r['id'],'LOGIN','users',r['id'])
     c.commit();return self.reply(200,{'ok':True}, {'Set-Cookie':'sa_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if os.environ.get('SA_SECURE_COOKIE')=='1' else '')})
    u,s=self.session(c)
    if method!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):raise Problem('Sessão inválida. Atualize a página.',403)
    if path=='/api/me' and method=='GET':return self.reply(200,{'user':u,'csrf':s['csrf']})
    if path=='/api/state' and method=='GET':return self.reply(200,state(c,u))
    if path=='/api/logout' and method=='POST':
     c.execute('DELETE FROM sessions WHERE token_hash=?',(s['token_hash'],));audit(c,u['id'],'LOGOUT','users',u['id']);c.commit();return self.reply(200,{'ok':True},{'Set-Cookie':'sa_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict'})
    if path=='/api/password' and method=='POST':
     p=self.body();old=p.get('current','');new=p.get('password','');password_policy(new)
     if not isinstance(old,str) or not verify(old,get(c,'users',u['id'])['password_hash']):raise Problem('Senha atual incorreta.')
     c.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new),u['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],));audit(c,u['id'],'PASSWORD','users',u['id']);c.commit();return self.reply(200,{'ok':True})
    if path=='/api/settings' and method=='PUT':
     if u['role']!='admin':raise Problem('Somente administrador.',403)
     p=self.body()
     try:a=float(p['min_grade']);f=float(p['min_attendance']);assert 0<=a<=10 and 0<=f<=100
     except (KeyError,ValueError,TypeError,AssertionError):raise Problem('Limites inválidos.')
     c.execute('UPDATE settings SET min_grade=?,min_attendance=? WHERE id=1',(a,f));audit(c,u['id'],'UPDATE','settings',1,json.dumps(p));c.commit();return self.reply(200,{'ok':True})
    if path=='/api/backup' and method=='POST':
     if u['role']!='admin':raise Problem('Somente administrador.',403)
     name=backup();audit(c,u['id'],'BACKUP','database',details=name.name);c.commit();return self.reply(200,{'ok':True,'file':name.name})
    parts=path.strip('/').split('/')
    if len(parts) in (2,3) and parts[1] in TABLES and method in ('POST','PUT','DELETE'):
     if (method=='POST' and len(parts)!=2) or (method!='POST' and (len(parts)!=3 or not parts[2].isdigit())):raise Problem('Rota inválida.',404)
     result=mutate(c,u,parts[1],self.body() if method!='DELETE' else {},method,int(parts[2]) if len(parts)==3 else None);c.commit();return self.reply(200,result)
    raise Problem('Rota não encontrada.',404)
  except Problem as e:self.reply(e.status,{'error':e.message})
  except sqlite3.IntegrityError as e:
   msg=str(e);self.reply(409,{'error':'Registro duplicado. Revise os identificadores e vínculos.' if 'UNIQUE' in msg else 'Registro possui vínculos: inative-o para preservar o histórico.' if 'FOREIGN KEY' in msg else 'Valores obrigatórios ou limites inválidos.'})
  except (ValueError,TypeError,KeyError) as e:self.reply(400,{'error':'Dados inválidos. Revise os campos obrigatórios.'})
  except Exception as e:
   print('Erro interno:',repr(e),flush=True);self.reply(500,{'error':'Falha interna. Consulte o terminal do servidor.'})
 def static(self,path):
  root=BASE/'docs' if path.startswith('/docs/') else BASE/'static'
  relative=path[6:] if path.startswith('/docs/') else ('index.html' if path=='/' else path.lstrip('/'))
  target=(root/relative).resolve()
  if not target.is_relative_to(root.resolve()) or not target.is_file():raise Problem('Arquivo não encontrado.',404)
  ext=target.suffix;mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.pdf':'application/pdf','.md':'text/plain; charset=utf-8'}.get(ext,'application/octet-stream')
  data=target.read_bytes();self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'");self.end_headers();self.wfile.write(data)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true');parser.add_argument('--port',type=int,default=8000);parser.add_argument('--backup',action='store_true');parser.add_argument('--restore',type=Path);args=parser.parse_args()
 if args.restore:
  if not args.restore.is_file():raise SystemExit('Backup não encontrado.')
  with sqlite3.connect(args.restore) as c:
   if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise SystemExit('Backup inválido.')
   for t in (*TABLES,'settings','audit','sessions'):c.execute('SELECT 1 FROM '+t+' LIMIT 1')
  if DB_PATH.exists():backup()
  DB_PATH.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(args.restore,DB_PATH)
  with connect() as c:c.execute('DELETE FROM sessions');audit(c,None,'RESTORE','database',details='Backup restaurado pelo operador local.')
  print('Restauração concluída.');raise SystemExit()
 init_db(args.demo)
 if args.backup:print(backup());raise SystemExit()
 threading.Thread(target=backup_loop,daemon=True).start()
 print(f'SA UniGoiás: http://127.0.0.1:{args.port} | Ctrl+C para encerrar',flush=True)
 try:ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
 except KeyboardInterrupt:print('\nServidor encerrado.')
