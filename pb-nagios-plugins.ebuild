# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4

DESCRIPTION="Additional Nagios plugins for usage by ProfitBricks."
HOMEPAGE="http://git.pb.local/gitweb/?p=python/nagios-plugin;a=summary"
SRC_URI=""
EGIT_REPO_URI="git://git/python/nagios-plugin.git"

inherit git-2 distutils user versionator

PB_CATEGORY="net-analyzer"

LICENSE="LGPL-3"
SLOT="0"
KEYWORDS="amd64"
IUSE="megaraid nrpe perl smart"

EGIT_BRANCH="master"
EGIT_COMMIT=$(replace_version_separator 3 '-')

RDEPEND="
	|| (
		virtual/python-argparse
		dev-python/argparse
	)
	~dev-python/nagios-plugin-${PV}
	nrpe? ( || (
		net-analyzer/nrpe
		virtual/nrpe
	) )
	perl? ( dev-perl/Nagios-Plugin )
	smart? ( sys-apps/smartmontools )
	megaraid? ( sys-block/megacli )
"
DEPEND="
	${RDEPEND}
"

REQUIRED_USE="megaraid? ( smart )"

pkg_setup() {
	python_set_active_version 2
	python_pkg_setup
}

src_prepare() {
	elog "Used GIT tag: '${EGIT_COMMIT}'."
	distutils_src_prepare
}

src_install() {

	dodir /usr/lib64
	dosym lib64 /usr/lib
	dodir /usr/lib64/nagios/plugins/pb

	distutils_src_install

	use smart || rm ${D}/usr/bin/check_smart_state

	rm -fv ${ED}/usr/lib*/python*/site-packages/*.egg-info
	rm -fv ${ED}/usr/lib*/python*/site-packages/nagios/*.py*
	rm -fvr ${ED}/usr/lib*/python*/site-packages/nagios/plugin
	rm -fvr ${ED}/usr/lib*/python*/site-packages/nagios/__pycache__

	einfo "Installing debian/changelog and README.txt"
	dodoc debian/changelog
	dodoc README.txt

	if use nrpe; then
		einfo "Performing /usr/share/pb-config-nagios-nrpe-server/nrpe.d/"
		dodir /usr/share/pb-config-nagios-nrpe-server/nrpe.d/
		insinto /usr/share/pb-config-nagios-nrpe-server/
		newins etc/nrpe.cfg-gentoo nrpe.cfg
		insinto /usr/share/pb-config-nagios-nrpe-server/nrpe.d/
		doins etc/nrpe.d/00_allowed_hosts.cfg
		doins etc/nrpe.d/10_pb-check.cfg
	fi

	for script in check_procs check_smart_state check_uname check_vg_free check_vg_state ; do
		src="${ED}/usr/lib/nagios/plugins/pb/${script}"
		link_tgt="../lib/nagios/plugins/pb/${script}"
		link="/usr/bin/${script}"
		if [ -f "${src}" ] ; then
			einfo "Creating symlink ${link} -> ${link_tgt}"
			dosym "${link_tgt}" "${link}"
		fi
	done

}

pkg_postinst() {
	python_mod_optimize nagios/plugins
}

pkg_postrm () {
	python_mod_cleanup nagios/plugins
}

# vim: filetype=ebuild ts=4 sw=4
