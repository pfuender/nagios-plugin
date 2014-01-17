# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4
PYTHON_COMPAT=( python{2_6,2_7,3_2,3_3} pypy2_0 )

DESCRIPTION="Python modules streamline writing Nagios plugins."
HOMEPAGE="http://git.pb.local/gitweb/?p=python/nagios-plugin;a=summary"
SRC_URI=""
EGIT_REPO_URI="git://git/python/nagios-plugin.git"

inherit git-2 distutils-r1 user versionator

PB_CATEGORY="dev-python"

LICENSE="LGPL-3"
SLOT="0"
KEYWORDS="amd64"
IUSE="doc"

EGIT_BRANCH="develop"
EGIT_COMMIT=$(replace_version_separator 3 '-')

RDEPEND="
	|| (
		virtual/python-argparse
		dev-python/argparse
	)
"

DEPEND="
	${RDEPEND}
	doc? (	dev-python/epydoc
			dev-python/docutils
	)
"

pkg_setup() {
	elog "Used GIT tag: '${EGIT_COMMIT}'."
	distutils-r1_src_prepare
}

src_install() {

	distutils-r1_src_install
	rm -rfv ${ED}/usr/lib*/nagios/
	rm -rfv ${ED}/usr/lib*/python*/site-packages/nagios/plugins/

	einfo "Installing debian/changelog and README.txt"
	dodoc debian/changelog
	dodoc README.txt

	if use doc; then
		einfo "Installing documentation ..."
		dodir "/usr/share/doc/${PF}"
		dodir "/usr/share/doc/${PF}/html"
		dodir "/usr/share/doc/${PF}/pdf"

		einfo "Creating epydoc html documentation"
		epydoc --html -v -o "${ED}/usr/share/doc/${PF}/html" "${S}/nagios" || ewarn "Could not create epydoc html documentation"
		einfo "Creating epydoc pdf documentation"
		epydoc --pdf -o "${ED}/usr/share/doc/${PF}/pdf" "${S}/nagios" || ewarn "Could not create epydoc pdf documentation"

	fi

}

