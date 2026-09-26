/* Jalali calendar adapter used by the recurrence widget.
 * The leap correction table and arithmetic mirror ICU PersianCalendar.
 */
(function (root) {
    'use strict';
    var recurrence = root.recurrence = root.recurrence || {};
    var nonLeap = {
        1502:1,1601:1,1634:1,1667:1,1700:1,1733:1,1766:1,1799:1,1832:1,
        1865:1,1898:1,1931:1,1964:1,1997:1,2030:1,2059:1,2063:1,2096:1,
        2129:1,2158:1,2162:1,2191:1,2195:1,2224:1,2228:1,2257:1,2261:1,
        2290:1,2294:1,2323:1,2327:1,2356:1,2360:1,2389:1,2393:1,2422:1,
        2426:1,2455:1,2459:1,2488:1,2492:1,2521:1,2525:1,2554:1,2558:1,
        2587:1,2591:1,2620:1,2624:1,2653:1,2657:1,2686:1,2690:1,2719:1,
        2723:1,2748:1,2752:1,2756:1,2781:1,2785:1,2789:1,2818:1,2822:1,
        2847:1,2851:1,2855:1,2880:1,2884:1,2888:1,2913:1,2917:1,2921:1,
        2946:1,2950:1,2954:1,2979:1,2983:1,2987:1
    };
    function leap(y) {
        if (nonLeap[y]) return false;
        if (nonLeap[y - 1]) return true;
        return ((25 * y + 11) % 33) < 8;
    }
    function monthLength(y, m) {
        if (m <= 6) return 31;
        if (m <= 11) return 30;
        return leap(y) ? 30 : 29;
    }
    function jdnGregorian(y, m, d) {
        var a = Math.floor((14 - m) / 12), yy = y + 4800 - a, mm = m + 12 * a - 3;
        return d + Math.floor((153 * mm + 2) / 5) + 365 * yy + Math.floor(yy / 4) - Math.floor(yy / 100) + Math.floor(yy / 400) - 32045;
    }
    function gregorianJdn(jdn) {
        var a = jdn + 32044, b = Math.floor((4 * a + 3) / 146097), c = a - Math.floor(146097 * b / 4);
        var d = Math.floor((4 * c + 3) / 1461), e = c - Math.floor(1461 * d / 4), m = Math.floor((5 * e + 2) / 153);
        return {gy: 100 * b + d - 4800 + Math.floor(m / 10), gm: m + 3 - 12 * Math.floor(m / 10), gd: e - Math.floor((153 * m + 2) / 5) + 1};
    }
    function first(y) { return 365 * (y - 1) + Math.floor((8 * y + 21) / 33) - (nonLeap[y - 1] ? 1 : 0); }
    function toGregorian(jy, jm, jd) {
        var jdn = 1948320 + first(jy) + (jm <= 6 ? (jm - 1) * 31 : 186 + (jm - 7) * 30) + jd - 1;
        return gregorianJdn(jdn);
    }
    function fromGregorian(gy, gm, gd) {
        var days = jdnGregorian(gy, gm, gd) - 1948320, jy = 1 + Math.floor((33 * days + 3) / 12053), doy = days - first(jy);
        if (doy === 365 && !leap(jy)) { jy++; doy = 0; }
        var jm = doy < 186 ? Math.floor(doy / 31) + 1 : Math.floor((doy - 6) / 30) + 1;
        var jd = jm <= 6 ? doy - (jm - 1) * 31 + 1 : doy - (186 + (jm - 7) * 30) + 1;
        return {jy: jy, jm: jm, jd: jd};
    }
    recurrence.jalali = {isLeapYear: leap, monthLength: monthLength, toGregorian: toGregorian, fromGregorian: fromGregorian};
    recurrence.display = recurrence.display || {};
    recurrence.display.months = ['Farvardin','Ordibehesht','Khordad','Tir','Mordad','Shahrivar','Mehr','Aban','Azar','Dey','Bahman','Esfand'];
    recurrence.display.months_short = recurrence.display.months.slice();
    recurrence.display.weekdays = ['Saturday','Sunday','Monday','Tuesday','Wednesday','Thursday','Friday'];
    recurrence.display.weekdays_short = ['Sat','Sun','Mon','Tue','Wed','Thu','Fri'];
    recurrence.weekdays = ['SA','SU','MO','TU','WE','TH','FR'];
    recurrence.SATURDAY = recurrence.SA = new recurrence.Weekday(0, null);
    recurrence.SUNDAY = recurrence.SU = new recurrence.Weekday(1, null);
    recurrence.MONDAY = recurrence.MO = new recurrence.Weekday(2, null);
    recurrence.TUESDAY = recurrence.TU = new recurrence.Weekday(3, null);
    recurrence.WEDNESDAY = recurrence.WE = new recurrence.Weekday(4, null);
    recurrence.THURSDAY = recurrence.TH = new recurrence.Weekday(5, null);
    recurrence.FRIDAY = recurrence.FR = new recurrence.Weekday(6, null);
    recurrence.date.isleap = function (date) {
        return leap(fromGregorian(date.getFullYear(), date.getMonth() + 1, date.getDate()).jy);
    };
    recurrence.date.weekday = function (date) {
        return (date.getDay() + 1) % 7;
    };
    recurrence.date.days_in_month = function (date) {
        var j = fromGregorian(date.getFullYear(), date.getMonth() + 1, date.getDate());
        return monthLength(j.jy, j.jm);
    };
    recurrence.DateFormat.prototype.Y = function () {
        return fromGregorian(this.data.getFullYear(), this.data.getMonth() + 1, this.data.getDate()).jy;
    };
    recurrence.DateFormat.prototype.j = function () {
        return fromGregorian(this.data.getFullYear(), this.data.getMonth() + 1, this.data.getDate()).jd;
    };
    recurrence.DateFormat.prototype.d = function () {
        return recurrence.string.rjust(String(this.j()), 2, '0');
    };
    recurrence.DateFormat.prototype.m = function () {
        return recurrence.string.rjust(String(fromGregorian(this.data.getFullYear(), this.data.getMonth() + 1, this.data.getDate()).jm), 2, '0');
    };
    recurrence.DateFormat.prototype.n = function () {
        return fromGregorian(this.data.getFullYear(), this.data.getMonth() + 1, this.data.getDate()).jm;
    };
    recurrence.DateFormat.prototype.F = function () {
        return recurrence.display.months[this.n() - 1];
    };
    recurrence.DateFormat.prototype.M = function () {
        return recurrence.display.months_short[this.n() - 1];
    };
    function pad(value, length) {
        value = String(value);
        while (value.length < length) value = '0' + value;
        return value;
    }
    function normalizeDigits(value) {
        var fa = '۰۱۲۳۴۵۶۷۸۹', ar = '٠١٢٣٤٥٦٧٨٩';
        return String(value).replace(/[۰-۹٠-٩]/g, function (digit) {
            var index = fa.indexOf(digit);
            return String(index >= 0 ? index : ar.indexOf(digit));
        });
    }
    function serializeDate(date) {
        var j = fromGregorian(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate());
        return pad(j.jy, 4) + pad(j.jm, 2) + pad(j.jd, 2) + 'T' +
            pad(date.getUTCHours(), 2) + pad(date.getUTCMinutes(), 2) + pad(date.getUTCSeconds(), 2) + 'Z';
    }
    function deserializeDate(text) {
        var value = normalizeDigits(text);
        var jy = parseInt(value.slice(0, 4), 10), jm = parseInt(value.slice(4, 6), 10), jd = parseInt(value.slice(6, 8), 10);
        var g = toGregorian(jy, jm, jd), hour = parseInt(value.slice(9, 11), 10) || 0;
        var minute = parseInt(value.slice(11, 13), 10) || 0, second = parseInt(value.slice(13, 15), 10) || 0;
        return new Date(Date.UTC(g.gy, g.gm - 1, g.gd, hour, minute, second));
    }
    recurrence.serialize = function (value) {
        var obj = value instanceof recurrence.Rule ? new recurrence.Recurrence({rrules: [value]}) : value;
        var lines = ['X-RECURRENCE-VERSION:2', 'CALSCALE:JALALI'];
        if (obj.dtstart) lines.push('DTSTART:' + serializeDate(obj.dtstart));
        if (obj.dtend) lines.push('DTEND:' + serializeDate(obj.dtend));
        function ruleText(rule) {
            var parts = [['FREQ', recurrence.frequencies[rule.freq]]];
            if (rule.interval != 1) parts.push(['INTERVAL', rule.interval]);
            if (rule.wkst) parts.push(['WKST', recurrence.weekdays[rule.wkst]]);
            if (rule.count != null) parts.push(['COUNT', rule.count]);
            else if (rule.until) parts.push(['UNTIL', serializeDate(rule.until)]);
            if (rule.skip && rule.skip != 'OMIT') parts.push(['SKIP', rule.skip]);
            recurrence.array.foreach(recurrence.byparams, function (param) {
                var values = rule[param] || [];
                if (values.length) parts.push([param.toUpperCase(), recurrence.array.foreach(values, function (item) { return String(item); }).join(',')]);
            });
            return recurrence.array.foreach(parts, function (part) { return part[0] + '=' + part[1]; }).join(';');
        }
        recurrence.array.foreach(obj.rrules || [], function (rule) { lines.push('RRULE:' + ruleText(rule)); });
        recurrence.array.foreach(obj.exrules || [], function (rule) { lines.push('EXRULE:' + ruleText(rule)); });
        recurrence.array.foreach(obj.rdates || [], function (date) { lines.push('RDATE:' + serializeDate(date)); });
        recurrence.array.foreach(obj.exdates || [], function (date) { lines.push('EXDATE:' + serializeDate(date)); });
        return lines.join('\n');
    };
    recurrence.deserialize = function (text) {
        var version = false, scale = false, result = new recurrence.Recurrence({});
        recurrence.array.foreach(String(text).split(/\r?\n/), function (line) {
            if (!line) return;
            var split = line.indexOf(':'), label = line.slice(0, split), value = line.slice(split + 1);
            if (label == 'X-RECURRENCE-VERSION') version = value == '2';
            else if (label == 'CALSCALE') scale = value == 'JALALI';
            else if (label == 'DTSTART') result.dtstart = deserializeDate(value);
            else if (label == 'DTEND') result.dtend = deserializeDate(value);
            else if (label == 'RDATE' || label == 'EXDATE') recurrence.array.foreach(value.split(','), function (item) { result[label == 'RDATE' ? 'rdates' : 'exdates'].push(deserializeDate(item)); });
            else if (label == 'RRULE' || label == 'EXRULE') {
                var options = {}, freq = 0;
                recurrence.array.foreach(value.split(';'), function (part) {
                    var pair = part.split('='), key = pair[0], values = pair.slice(1).join('=').split(',');
                    if (key == 'FREQ') freq = recurrence.frequencies.indexOf(values[0]);
                    else if (key == 'WKST') options.wkst = recurrence.to_weekday(values[0]);
                    else if (key == 'UNTIL') options.until = deserializeDate(values[0]);
                    else if (key == 'BYDAY') options.byday = recurrence.array.foreach(values, recurrence.to_weekday);
                    else if (key == 'SKIP') options.skip = values[0];
                    else options[key.toLowerCase()] = parseInt(values[0], 10);
                });
                result[label == 'RRULE' ? 'rrules' : 'exrules'].push(new recurrence.Rule(freq, options));
            }
        });
        if (!version || !scale) throw new Error('legacy or non-Jalali recurrence data is unsupported');
        return result;
    };
    if (recurrence.widget && recurrence.widget.Calendar) {
        var Calendar = recurrence.widget.Calendar.prototype;
        Calendar.init = function (date, options) {
            this.date = date || recurrence.widget.date_today();
            var j = fromGregorian(this.date.getFullYear(), this.date.getMonth() + 1, this.date.getDate());
            this.month = j.jm - 1;
            this.year = j.jy;
            this.options = options || {};
            this.onchange = this.options.onchange;
            this.onclose = this.options.onclose;
            this.init_dom();
            this.show_month(this.year, this.month);
        };
        Calendar.get_month_grid = function (year, month) {
            var calendar = this, g = toGregorian(year, month + 1, 1);
            var start = (new Date(Date.UTC(g.gy, g.gm - 1, g.gd)).getUTCDay() + 1) % 7;
            var days = monthLength(year, month + 1), rows = Math.ceil((days + start) / 7) + 1;
            var grid = new recurrence.widget.Grid(7, rows), number = 1;
            recurrence.array.foreach(grid.cells, function (cell, i) {
                if (i < 7) {
                    cell.innerHTML = recurrence.display.weekdays_oneletter[i] || recurrence.display.weekdays_short[i].slice(0, 1);
                    recurrence.widget.add_class(cell, 'header');
                } else if (i - 7 < start || number > days) {
                    recurrence.widget.add_class(cell, 'empty');
                } else {
                    recurrence.widget.add_class(cell, 'day');
                    var current = fromGregorian(calendar.date.getFullYear(), calendar.date.getMonth() + 1, calendar.date.getDate());
                    if (current.jy == year && current.jm == month + 1 && current.jd == number) recurrence.widget.add_class(cell, 'active');
                    cell.innerHTML = number;
                    cell.onclick = function () { calendar.set_date(year, month, parseInt(this.innerHTML, 10)); };
                    number++;
                }
            });
            return grid;
        };
        Calendar.set_date = function (year, month, day) {
            var g = toGregorian(year, month + 1, day);
            this.date.setTime(new Date(g.gy, g.gm - 1, g.gd, this.date.getHours(), this.date.getMinutes(), this.date.getSeconds()).getTime());
            this.month = month;
            this.year = year;
            this.show_month(year, month);
            if (this.onchange) this.onchange(this.date);
        };
        Calendar.show_prev_year = function () { this.year--; this.show_month(this.year, this.month); };
        Calendar.show_next_year = function () { this.year++; this.show_month(this.year, this.month); };
        Calendar.show_prev_month = function () { if (--this.month < 0) { this.month = 11; this.year--; } this.show_month(this.year, this.month); };
        Calendar.show_next_month = function () { if (++this.month > 11) { this.month = 0; this.year++; } this.show_month(this.year, this.month); };
        var DateSelector = recurrence.widget.DateSelector.prototype;
        DateSelector.set_date = function (datestring) {
            var tokens = normalizeDigits(String(datestring)).replace(/\//g, '-').split('-');
            var year = parseInt(tokens[0], 10), month = parseInt(tokens[1], 10), day = parseInt(tokens[2], 10);
            try {
                if (!year || !month || !day || day > monthLength(year, month)) throw new Error('invalid date');
                var g = toGregorian(year, month, day);
                var current = this.date ? fromGregorian(this.date.getFullYear(), this.date.getMonth() + 1, this.date.getDate()) : null;
                if (!current || current.jy != year || current.jm != month || current.jd != day) {
                    if (!this.date) this.date = recurrence.widget.date_today();
                    this.date.setTime(new Date(g.gy, g.gm - 1, g.gd, this.date.getHours(), this.date.getMinutes(), this.date.getSeconds()).getTime());
                    this.elements.date_field.value = year + '-' + pad(month, 2) + '-' + pad(day, 2);
                    if (this.onchange) this.onchange(this.date);
                }
            } catch (error) {
                if (this.date && !this.options.allow_null) this.elements.date_field.value = recurrence.date.format(this.date, '%Y-%m-%d');
                else { this.elements.date_field.value = ''; if (this.onchange) this.onchange(null); }
            }
        };
    }
})(typeof window !== 'undefined' ? window : this);
