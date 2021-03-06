<!-- Landscape | [![Code Health](https://landscape.io/github/ucoin-io/sakia/dev/landscape.svg?style=flat)](https://landscape.io/github/ucoin-io/sakia/dev) -->

![sakia logo](https://raw.github.com/ucoin-io/sakia/master/sakia.png)

Sakia [![Coverage Status](https://coveralls.io/repos/ucoin-io/sakia/badge.svg?branch=dev)](https://coveralls.io/r/ucoin-io/sakia) [![Build Status](https://travis-ci.org/ucoin-io/sakia.svg?branch=travis)](https://travis-ci.org/ucoin-io/sakia) [![Build status](https://ci.appveyor.com/api/projects/status/nd7idaoi6s2fpsqy/branch/dev)](https://ci.appveyor.com/project/Insoleet/sakia/branch/dev) [![Translation status](http://weblate.ucoin.io/widgets/sakia/-/svg-badge.svg)](http://weblate.ucoin.io/engage/sakia/?utm_source=widget)
========

Python3 and PyQt5 Client for [uCoin](http://www.ucoin.io) project.


## Goal features
  * Ucoin account management via wallets and communities
  * Multi-currency
  * Multi-community
  * Multi-wallets
  * Contacts management
  * User-friendly money transfer
  * Community membership management

## Current state
### Done (master branch)
  * Accounts management
  * Communities viewing
  * Money Transfer
  * cx_freeze deployment
  * Wallets management
  * Contacts management
  * Joining a community, publishing keys
  * Multiple wallets management

### Dependencies
  * Dependencies :
   * [python3](https://www.python.org/downloads/)
   * [cx_freeze for python 3](http://cx-freeze.sourceforge.net/)
   * [pyqt5](http://www.riverbankcomputing.co.uk/software/pyqt/download5)
   * [libsodium](http://doc.libsodium.org/installation/README.html)
  * Python libraries dependencies :
   * __ucoinpy__

  * General tips : use pyenv to build sakia, as described in the [wiki](https://github.com/ucoin-io/sakia/wiki/Cutecoin-install-for-developpers)

### Build scripts
  * Run __python3 gen_resources.py__ in sakia folder
  * Run __python3 gen_translations.py__ in sakia folder
  * Run __python3 setup.py build__ in sakia folder
  * The executable is generated in "build" folder, named "sakia"

### Download latest release
  * Go to [current release](https://github.com/ucoin-io/sakia/releases)
  * Download corresponding package to your operating system
  * Unzip and start "sakia" :)
  * Join our beta community by contacting us on [uCoin forum](http://forum.ucoin.io/)

## License
This software is distributed under [GNU GPLv3](https://raw.github.com/ucoin-io/sakia/dev/LICENSE).
