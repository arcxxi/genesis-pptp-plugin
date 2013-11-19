import os
import re
import socket


from genesis.api import *
from genesis.com import *
from genesis.utils import *
from subprocess import *



class PptpConfig(Plugin):
    implements(IConfigurable)
    name = 'Pptp'
    id = 'pptp'
    iconfont = 'gen-upload-2'
    shares = {}
    general = {}
    users = {}
    userlist = []
    passlist = {}
    srvlist = []
    fields = []
    tmp = {}
    cfg_file2 = '/etc/pptpd.conf'
    service_file_path_script = '/etc/systemd/system/pptb_genesis.script.sh'

    general_defaults = {
        'gateway': '192.168.178.1',
        'localip': '192.168.178.2',
        'ipfrom': '192.168.178.100',
        'ipto': '192.168.178.255'
    }

    def __init__(self):
        self.cfg_file = self.app.get_config(self).cfg_file

    def setConfigParameter(self,param,arg):
        self.tmp[param] = arg

    def startService(self):
        self.log.info("Starting service")
        service_file_path = '/etc/systemd/system/pptb_genesis.service'
        if not os.path.exists(service_file_path):
            self.log.info("Creating new pptpd service")
            f = open(service_file_path, 'a')
            f.write("[Unit]\n")
            f.write("Description=Autostart script for pptp\n")
            f.write("[Install]\n")
            f.write("WantedBy=multi-user.target\n")
            f.write("[Service]\n")
            f.write("Type=oneshot\n")
            f.write("RemainAfterExit=yes\n")
            f.write("ExecStart=" + self.service_file_path_script + '\n')
            f.close()
            f = open(self.service_file_path_script,"a")
            f.write("iptables -A INPUT -i ppp+ -j ACCEPT \n")
            f.write("iptables -A OUTPUT -o ppp+ -j ACCEPT \n")
            f.write("iptables -A INPUT -p tcp --dport 1723 -j ACCEPT \n")
            f.write("iptables -A INPUT -p 47 -j ACCEPT \n")
            f.write("iptables -A OUTPUT -p 47 -j ACCEPT \n")
            f.write("iptables -F FORWARD \n")
            f.write("iptables -A FORWARD -j ACCEPT \n")
            f.write("iptables -A POSTROUTING -t nat -o eth0 -j MASQUERADE \n")
            f.write("iptables -A POSTROUTING -t nat -o ppp+ -j MASQUERADE \n")
            f.close() 
            os.chmod(self.service_file_path_script, 0744)
            shell(self.service_file_path_script)
        x = shell("systemctl is-enabled pptb_genesis.service")       
        if (not x is None) and (x.strip().find("enabled") != 0):
           shell("systemctl enable pptb_genesis.service")
        x = shell("systemctl is-enabled pptpd.service")       
        if (not x is None) and (x.strip().find("enabled") != 0):
           shell("systemctl enable pptpd.service")
        shell("systemctl start pptpd.service")

    def replaceInService(self,identifierKey,replacement):
        f = open(self.service_file_path_script,"r")
        lines = f.readlines()
        f.close()
        replaced = False
        for i in range(len(lines)):
            if lines[i].strip().find(identifierKey) == 0:
               lines[i] = replacement
               replaced = True
            lines[i] = lines[i].replace('\n','')
        f = open(self.service_file_path_script,"w")
        f.write('\n'.join(lines))
        if not replaced == True:
            f.write('\n' + replacement.replace('\n','')+'\n')
        f.close()


    def isIP(self, ip):
        try:
           socket.inet_aton(ip)
           split_ip = ip.split('.')
           return len(split_ip)==4
        except socket.error:
           return False

    def checkRange(self,a,b):
        split_a = a.split('.')
        split_b = b.split('.')
        i = 0
        while i < 4: 
           ia = int(split_a[i])
           ib = int(split_b[i])
           if ia > ib:
              return False
           i += 1
        return True

    def setGateway(self,gate):
        r = "ip route delete " + self.general['gateway'] + " dev eth0"
        self.log.info("Remove old rule: " + r)
        shell(r)
        r = "ip route add 0.0.0.0 via " + gate + " dev eth0"
        self.log.info("Add new rule: " + r)
        shell(r)
        self.replaceInService("ip route add 0.0.0.0 via",r)
        self.app.config.set('pptp', 'gateway', gate)
        self.app.config.save()

    def enableIP4(self):
       self.log.info("Enable IPv4 forwarding.")
       fileName = "/etc/sysctl.d/99-sysctl.conf"
       if not os.path.exists(fileName):
            f = open(fileName, 'a')
            f.write("net.ipv4.ip_forward=1")
            f.close()
            shell("sysctl --system")
            shell("echo 1 > /proc/sys/net/ipv4/ip_forward")
       else:
           f = open(fileName)
           ss = f.readlines()
           f.close()
           isSet = False
           for s in ss:
               s = s.strip()
               if s.find('net.ipv4.ip_forward=1') == 0:
                  isSet = True
           if not isSet:
              f = open(fileName, "a")
              f.write("net.ipv4.ip_forward=1")
              f.close()
              shell("sysctl --system")
              shell("echo 1 > /proc/sys/net/ipv4/ip_forward")
       

    def setPPTPOptions(self):
        s = ""
        s += "name pptpd #Name des Pptp-Servers" + '\n'
        s += "refuse-pap #pap verweigern" + '\n'
        s += "refuse-chap #chap verweigern" + '\n'
        s += "refuse-mschap #mschap verweigern" + '\n'
        s += "require-mschap-v2 #mschap Version 2 verlangen" + '\n'
        s += "require-mppe-128 #Verschluesselung verlangen" + '\n'
        s += "lock" + '\n'
        s += "nobsdcomp" + '\n'
        s += "novj" + '\n'
        s += "novjccomp" + '\n'
        s += "nologfd" + '\n'
        s += "ms-dns 8.8.8.8 #Dns-Server 1." + '\n'
        s += "ms-dns 8.8.4.4 #Dns-Server 2." + '\n'
        ConfManager.get().save('pptp', '/etc/ppp/pptpd-options', s)
        ConfManager.get().commit('pptp')

    def setIPConfig(self,local_ip,from_ip,to_ip):
        content = []
        added_local_ip = False
        added_range = False
        added_option = False
        if not os.path.exists(self.cfg_file2):
            open(self.cfg_file2, 'a').close()
        ss = ConfManager.get().load('pptp', self.cfg_file2).split('\n')
        cs = ''
        for s in ss:
                s = s.strip()
                if s.find('listen') == 0:
                    content.append("listen " + local_ip)
                    added_local_ip = True
                elif s.find('remoteip') == 0:
                    content.append("remoteip " + from_ip + "-" + self.toIPRange(from_ip,to_ip))
                    added_range = True
                elif s.find('option /etc/ppp/pptpd-options') == 0:
                    added_option = True
                    content.append(s)
                else:
                    content.append(s)
        if not added_local_ip:
	     content.append("listen " + local_ip)
        if not added_range:
	     content.append("remoteip " + from_ip + "-" + self.toIPRange(from_ip,to_ip))
        if not added_option:
            content.insert(0,"option /etc/ppp/pptpd-options")
            self.setPPTPOptions()
        content.append("")
        ConfManager.get().save('pptp', self.cfg_file2, '\n'.join(content))
        ConfManager.get().commit('pptp')

   
    def storeConfig(self):
        err = ""
        if (self.tmp['gateway'] != self.general['gateway']):
            if not self.isIP(self.tmp['gateway']):
               err += "Gateway must be an ip address"
        if (self.tmp['localip'] != self.general['localip']):
            if not self.isIP(self.tmp['localip']):
               err += "Local ip must be an ip address"
        if (self.tmp['ipfrom'] != self.general['ipfrom']):
            if not self.isIP(self.tmp['ipfrom']):
               err += "IP range must be an ip address"
        if (self.tmp['ipto'] != self.general['ipto']):
            if not self.isIP(self.tmp['ipto']):
               err += "IP range must be an ip address"
        if (not self.checkRange(self.tmp['ipfrom'],self.tmp['ipto'])):
            err += "The first address in range has to be less than the second"
        if err == "":
            if (self.tmp['gateway'] != self.general['gateway']):
                self.setGateway(self.tmp['gateway'])
                self.general['gateway'] = self.tmp['gateway']
            if (self.tmp['localip'] != self.general['localip']) or (self.tmp['ipfrom'] != self.general['ipfrom']) or (self.tmp['ipto'] != self.general['ipto']):
                self.setIPConfig(self.tmp['localip'],self.tmp['ipfrom'],self.tmp['ipto'])
                self.general['localip'] = self.tmp['localip']
                self.general['ipfrom'] = self.tmp['ipfrom']
                self.general['ipto'] = self.tmp['ipto']
            return None
        else:
            return err

    def list_files(self):
        return [self.cfg_file]

    def load_server_config(self):
        return None

    def toIPRange(self,a,b):
        self.log.info("Do range: " + a + "-" + b)
        a_ip = a.split(".")
        b_ip = b.split(".")
        i = 0
        result = ""
        doAgain = False
        while i < 4: 
           ia = int(a_ip[i])
           ib = int(b_ip[i])
           if ia != ib:
              doAgain = True
           if doAgain == True:
              result += "." + b_ip[i]
           i += 1
        if (result[0] == "."):
           result = result[1:]
        return result


    def getIPRange(self,a,b):
        a_ip = a.split(".")
        b_ip = b.split(".")
        if len(b_ip) == 1:
           return a_ip[0] + "." + a_ip[1] + "." + a_ip[2] + "." + b_ip[0]
        elif len(b_ip) == 2:
           return a_ip[0] + "." + a_ip[1] + "." + b_ip[0] + "." + b_ip[1]
        elif len(b_ip) == 3:
           return a_ip[0] + "." + b_ip[0] + "." + b_ip[1] + "." + b_ip[2]
        else:
           return b

    def getConfig(self,c = None):
        if c is None:
            return self.general 
#        self.log.info("Get config: " + c);
#        for h in self.general:
#            self.log.info("Has value" + h + " -> " + self.general[h])
        return self.general[c];

    def load(self):
        self.userlist = []
        self.shares = {}
        self.passlist = {}
        self.srvlist = []
        self.general = self.general_defaults.copy()
        try:
            self.general['localip'] = ip = socket.gethostbyaddr(socket.gethostname())[-1][0]
        except:
            pass
        if os.path.exists(self.cfg_file):
            fn = self.cfg_file
        else:
            fn = self.cfg_file + '.default'
        ss = ConfManager.get().load('pptp', fn).split('\n')
        cs = ''
        for s in ss:
                s = s.strip()
                if len(s) >= 1 and s[0] != '#' and s[0] != ';':
                    items = s.split()
                    if len(items) < 3:
                         continue
                    usr = items[0]
                    usr = usr.strip()
                    srv = items[1]
                    srv = srv.strip()
                    psw = items[2]
                    psw = psw.strip()
                    if srv == "pptpd":
                         self.userlist.append(usr)
                         self.passlist[usr] = psw
                    else:
                         self.srvlist.append(s)
                else:
                    self.srvlist.append(s)


        if not os.path.exists(self.cfg_file2):
            open(self.cfg_file2, 'a').close()
        ss = ConfManager.get().load('pptp', self.cfg_file2).split('\n')
        cs = ''
        for s in ss:
                s = s.strip()
                if s.find('listen') == 0:
                    self.general["localip"] = str(s[7:]).strip()
                elif s.find('remoteip') == 0:
                    s = s[9:]
                    ips = s.split("-")
                    if len(ips) == 2:
                       self.general['ipfrom'] = ips[0].strip()
                       range = self.getIPRange(ips[0].strip(),ips[1].strip())
                       self.general['ipto'] = range

        if self.app.config.has_option('pptp', 'gateway'):
            self.general['gateway'] = self.app.config.get('pptp', 'gateway')
    
      
    def save(self):
        ss = ''
        for k in self.srvlist:
              ss+= "" +k + '\n'
        for h in self.userlist:
              ss += "" + h + " pptpd " + self.passlist[h] + " *" + '\n'
        ConfManager.get().save('pptp', self.cfg_file, ss)
        ConfManager.get().commit('pptp')

    def delete_user(self,usr):
        self.userlist.remove(usr)

    def set_new_password(self, usr, psw):
        self.passlist[usr] = psw

    def get_userlist(self):
        return self.userlist

    def add_to_userlist(self, usr, psw):
        self.userlist.append(usr)
        self.passlist[usr] = psw
        with open(self.cfg_file, 'a') as f:
            f.write('' + usr + ' pptpd ' + psw + ' *\n')


class GeneralConfig(ModuleConfig):
    target=PptpConfig
    platform = ['debian', 'centos', 'arch', 'arkos', 'gentoo', 'mandriva']
    
    labels = {
        'cfg_file': 'Configuration file'
    }
    
    cfg_file = '/etc/ppp/chap-secrets'
   
   
class BSDConfig(GeneralConfig):
    implements((IModuleConfig, -100))
    platform = ['freebsd']
    
    cfg_file = '/usr/local/etc/ppp/chap-secrets'
 