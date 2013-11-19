from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis.utils import *
from genesis import apis

import backend


class PptpPlugin(CategoryPlugin):
    text = 'PPTP VPN'
    iconfont = 'gen-upload-2'
    folder = 'servers'
    services = [('Samba', 'smbd')]
    
    def on_session_start(self):
        self.log.info("Start PPTP Plugin session")
        self._tab = 0
        self._cfg = backend.PptpConfig(self.app)
        self._cfg.startService()
        self._cfg.load()
        self._editing_user = None
        self._adding_user = False
        self._cfg.enableIP4()

    def get_ui(self):
        ui = self.app.inflate('pptp:main')
        ui.find('tabs').set('active', self._tab)
        # User
        for h in self._cfg.get_userlist():
            r = UI.DTR(
                    UI.IconFont(iconfont='gen-user'),
                    UI.Label(text=h),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-pencil-2',
                            text='Set password', id='edit_user/' + h),
                        UI.TipIcon(
                            iconfont='gen-close',
                            text='Delete', id='del_user/' + h, warning='Delete user %s'%h)
                    ),
                )
            ui.append('users', r)
           
        if not self._adding_user:
            ui.remove('dlgAddNewUser')

        if not self._editing_user is None:
            if not self._editing_user in self._cfg.get_userlist():
                    self.put_message('err', 'User "' + self._editing_user + '" not found')
                    self._editing_user = None
#            else:
#	             ui.append('main', UI.InputBox(
#                         title='Set password for' + self._editing_user,
#                         text='Password:',
#                         id='dlgChangeUserPassword'
#                    ))

        if self._editing_user is None:
	     ui.remove('dlgSetPsw')
 
        
        for h in self._cfg.getConfig():
            if not ui.find(h) is None:
               ui.find(h).set('value',self._cfg.getConfig(h))	

        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'restart':
            backend.restart()
        if params[0] == 'edit_user':
            self._editing_user = params[1]
            self._tab = 0
        if params[0] == 'del_user':
            if params[1] in self._cfg.get_userlist():
                self._cfg.delete_user(params[1])
                self._cfg.save()
                self.put_message('info','User "' + params[1] + '" deleted.')
            else:
                self.put_message('err','User "' + params[1] + '" not found.')
            self._tab = 0
        if params[0] == 'newuser':
            self._adding_user = True

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgAddNewUser':
            if vars.getvalue('action', '') == 'OK':
                v = vars.getvalue('login', '')
                p = vars.getvalue('password','')
                if v == '' or p == '':
                    self.put_message('err', 'Username or password must be set.')  
                else:
                    self._cfg.add_to_userlist(v,'huch')
            self._adding_user = False

        if params[0] == 'dlgChangeUserPassword':
            if vars.getvalue('action', '') == 'OK':
                v = vars.getvalue('value', '')
                self._cfg.set_new_password(self._editing_user,v)
                self._cfg.save()
                self.put_message('info','Password changed for user "' + self._editing_user + '"')
            self._editing_user = None

        if params[0] == 'dlgSetPsw':
            if vars.getvalue('action', '') == 'OK':
                v = vars.getvalue('password', '')
                self._cfg.set_new_password(self._editing_user,v)
                self._cfg.save()
                self.put_message('info','Password changed for user "' + self._editing_user + '"')
            self._editing_user = None

        if params[0] == 'frmChangeGeneralCfg':
            for a in self._cfg.getConfig():
                tmp = vars.getvalue(a,'')
                self._cfg.setConfigParameter(a,tmp)
            res = self._cfg.storeConfig()
            if not res is None:
                self.put_message('err',res)
            else:
                self.put_message('info',"New configuration stored and set.")
            self._tab = 1
