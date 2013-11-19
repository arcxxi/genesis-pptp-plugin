genesis-pptp-plugin
===================

A plugin for genesis to configure a vpn server on arkOS.

This plugin is only beta and for testing. If the content
is put into an archive *.tar.gz, it can be uploaded into
genesis.

You can configure your own pptpd-server. But you will need
the pptpd-service, which is not in the mirrorlist of arkOS.
So you have to add the new mirror to `/etc/pacman.d`

	[community]
	Server=http://ftp.f3l.de/archlinuxarm/armv6h/community/

After adding this, install the `pptpd server`:

	pacman -S pptpd

