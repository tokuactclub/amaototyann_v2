# ワーカーを増やす（＝プロセスを増やす）と、データの共有をモジュールで行っているがために、データが共有されなくなる。
# そのため、ワーカーは1つにしている。
# もし、ワーカーを増やす場合は、データの共有を行う方法を考える必要がある。
# もしくは、gunicornの--worker-classをgeventにして、非同期で処理速度を向上させる
# どうやらこれを利用するとエラーが出るので、一旦単一ワーカーで動かす。まあ大丈夫っしょ。
# gunicorn amaototyann.src.server:app --worker-class gevent --timeout 300 -w 1
gunicorn amaototyann.src.server:app  --timeout 300 -w 1

