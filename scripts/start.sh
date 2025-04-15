# ワーカーを増やす（＝プロセスを増やす）と、データの共有をモジュールで行っているがために、データが共有されなくなる。
# そのため、ワーカーは1つにしている。
# もし、ワーカーを増やす場合は、データの共有を行う方法を考える必要がある。
# 現在は、gunicornの--worker-classをgeventにして、非同期で処理速度を向上させる
gunicorn amaototyann.src.server:app --worker-class gevent --timeout 300 -w 1

