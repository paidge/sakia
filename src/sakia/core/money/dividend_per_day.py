from PyQt5.QtCore import QObject, QCoreApplication, QT_TRANSLATE_NOOP, QLocale
from .base_referential import BaseReferential
from .udd_to_past import UDDToPast

from PyQt5.QtCore import QCoreApplication, QT_TRANSLATE_NOOP, QLocale


class DividendPerDay(BaseReferential):
    _NAME_STR_ = QT_TRANSLATE_NOOP('DividendPerDay', 'UDD')
    _REF_STR_ = QT_TRANSLATE_NOOP('DividendPerDay', "{0} {1}UDD {2}")
    _UNITS_STR_ = QT_TRANSLATE_NOOP('DividendPerDay', "UDD {0}")
    _FORMULA_STR_ = QT_TRANSLATE_NOOP('DividendPerDay',
                                      """UDD(t) = (Q * 100) / (UD(t) / DT)
                                        <br >
                                        <table>
                                        <tr><td>R</td><td>Dividend per day in percent</td></tr>
                                        <tr><td>t</td><td>Last UD time</td></tr>
                                        <tr><td>Q</td><td>Quantitative value</td></tr>
                                        <tr><td>UD</td><td>Universal Dividend</td></tr>
                                        <tr><td>DT</td><td>Delay between two UD in days</td></tr>
                                        </table>"""
                                      )
    _DESCRIPTION_STR_ = QT_TRANSLATE_NOOP('DividendPerDay',
                                          """Universal Dividend per Day displayed in percent.
                                          The purpose is to have a default unit that is easy to use and understand.
                                          100 UDD equal the Universal Dividend created per day.
                                          """.replace('\n', '<br >'))

    def __init__(self, amount, community, app, block_number=None):
        super().__init__(amount, community, app, block_number)

    @classmethod
    def instance(cls, amount, community, app, block_number=None):
        if app.preferences['forgetfulness']:
            return UDDToPast(amount, community, app, block_number)
        else:
            return cls(amount, community, app, block_number)

    @classmethod
    def translated_name(cls):
        return QCoreApplication.translate('DividendPerDay', DividendPerDay._NAME_STR_)

    @property
    def units(self):
        return QCoreApplication.translate("DividendPerDay", DividendPerDay._UNITS_STR_).format(self.community.short_currency)

    @property
    def formula(self):
        return QCoreApplication.translate('DividendPerDay', DividendPerDay._FORMULA_STR_)

    @property
    def description(self):
        return QCoreApplication.translate("DividendPerDay", DividendPerDay._DESCRIPTION_STR_)

    @property
    def diff_units(self):
        return self.units

    async def value(self):
        """
        Return relative value of amount

        value = (Q * 100) / R
        Q = Quantitative value
        R = UD(t) of one day
        t = last UD block time

        :param int amount:   Value
        :param sakia.core.community.Community community: Community instance
        :return: float
        """
        dividend = await self.community.dividend()
        params = await self.community.parameters()
        if dividend > 0:
            return (self.amount * 100) / (float(dividend) / (params['dt'] / 86400))
        else:
            return self.amount

    async def differential(self):
        return await self.value()

    async def localized(self, units=False, international_system=False):
        value = await self.value()
        prefix = ""
        localized_value = QLocale().toString(float(value), 'f', self.app.preferences['digits_after_comma'])

        if units or international_system:
            return QCoreApplication.translate("Relative", DividendPerDay._REF_STR_) \
                .format(localized_value,
                        prefix,
                        self.community.short_currency if units else "")
        else:
            return localized_value

    async def diff_localized(self, units=False, international_system=False):
        value = await self.differential()
        prefix = ""
        localized_value = QLocale().toString(float(value), 'f', self.app.preferences['digits_after_comma'])

        if units or international_system:
            return QCoreApplication.translate("Relative", DividendPerDay._REF_STR_) \
                .format(localized_value,
                        prefix,
                        self.community.short_currency if units else "")
        else:
            return localized_value
