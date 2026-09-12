"""Noninteractive UI checks for source and packaged Windows builds."""
import json
import time
from pathlib import Path
from unittest.mock import patch


def run(output):
    from ui import LaptopCheckApp
    app = LaptopCheckApp()
    app.withdraw()
    try:
        app.update()
        app.toggle(); app.update()
        assert app.lang == 'bn'
        app.toggle()
        with patch('ui.messagebox.askyesno', return_value=True):
            app.reset()
        assert not app.scanned
        with patch('ui.auto_scan', side_effect=RuntimeError('simulated scan failure')), \
             patch('ui.messagebox.showerror') as error:
            app.scan()
            deadline=time.monotonic()+5
            while app.busy and time.monotonic()<deadline:
                app.update(); time.sleep(.01)
            assert not app.busy, 'Scan did not recover'
            assert str(app.scanb['state'])=='normal'
            error.assert_called_once()
        with patch('ui.auto_scan', return_value=([], {'serial':'TEST'})):
            app.scan()
            # A manual result recorded during the scan must survive completion.
            app._manual('Keyboard Test').update(status='PASS',value='Passed')
            deadline=time.monotonic()+5
            while app.busy and time.monotonic()<deadline:
                app.update(); time.sleep(.01)
            assert app.scanned and not app.busy
            assert app._manual('Keyboard Test')['status']=='PASS'
        app._done([], {'serial':'DIFFERENT'})
        assert app._manual('Keyboard Test')['status']=='MANUAL'
        app.update()
        Path(output).write_text(json.dumps({'result':'PASS','checks':['startup','language toggle','new inspection','scan exception recovery','scan completion','manual result preservation','different laptop reset']}),encoding='utf-8')
    finally:
        app.destroy()


if __name__ == '__main__':
    import sys
    run(sys.argv[1])
