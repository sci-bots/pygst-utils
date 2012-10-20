import time
from subprocess import check_output

from pygst_utils.video_pipeline.window_service_proxy import server_popen,\
        WindowServiceProxy
from jsonrpclib import Server


def test_window_service():
    server_process = server_popen(8080)
    server = Server('http://localhost:8080')
    time.sleep(3)
    print check_output('pgrep -fl python.*server', shell=True)
    print server_process.pid, server.system.listMethods()
    server_process.kill()


def test_window_service_proxy():
    with WindowServiceProxy() as w:
        print w.get_video_mode_map()
        print w.select_video_caps()
    print 'WindowServiceProxy closed successfully'


def main():
    test_window_service_proxy()


if __name__ == '__main__':
    main()
