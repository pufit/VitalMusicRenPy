init -999 python:
    import threading
    import time
    import collections
    from contextlib import contextmanager

    from influxdb import InfluxDBClient

    class Metrics(object):
        __slots__ = ('client', 'user', '_funcs_stat', '_counter')
        
        def __init__(self):
            host, port = METRICS_ADDRESS.split(':')
            self.client = InfluxDBClient(host=host, port=int(port), database=METRICS_DB_NAME)
            self.user = (os.getenv('USERNAME') or os.getenv('USER')).encode('ascii', 'xmlcharrefreplace')
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            
            self._funcs_stat = collections.defaultdict(int)
            self._counter = collections.defaultdict(int)
            
            self.thread.start()
            self.info()
        
        def get_info(self):
            return {
                'os_name': os.name,
                'user': self.user,
                'uuid': uuid,
            }
        
        def event(self, event_type, fields, tags=None):
            tags = tags or {}
            tags['uuid'] = uuid
            tags['user'] = self.user
            
            self.client.write_points([
                {
                    'measurement': event_type,
                    'tags': tags,
                    'fields': fields,
                }
            ])
        
        def _run(self):
            counter = 0
            while True:
                self.event('tick', {
                    'spent_time': counter,
                })
                
                counter += 1
                time.sleep(1)
        
        def info(self):
            self.event('info', self.get_info())
        
        def measure(self, prefix):
            def decorator(func):
                def _wraps(*args, **kwargs):
                    t = time.time()
                    res = func(*args, **kwargs)
                    
                    name = '{}_func_{}'.format(prefix, func.__name__)
                    
                    self._funcs_stat[name] += 1
                    self.event(name, {
                        'spent_time': time.time() - t,
                        'call_count': self._funcs_stat[name],
                    })
                    
                    return res
                return _wraps
            return decorator

        @contextmanager
        def context_measure(self, name):
            t = time.time()

            try:
                yield
            finally:
                self.event(name, {
                    'spent_time': time.time() - t,
                })

        def increment(self, event_type):
            self._counter[event_type] += 1
            self.event(event_type, {
                'count': self._counter[event_type],
            })

    metrics = Metrics()
