package com.andreia.calculator;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

/**
 * Evaluates expressions as they appear on the display: digits with ',' as the
 * decimal separator, + − × ÷, postfix %, parentheses and implicit
 * multiplication such as 2(3+4).
 */
public final class Calculator {

    public static final class CalcException extends Exception {
        public final boolean divisionByZero;

        CalcException(String message, boolean divisionByZero) {
            super(message);
            this.divisionByZero = divisionByZero;
        }
    }

    private static final MathContext MC = new MathContext(20, RoundingMode.HALF_EVEN);
    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);

    private final String s;
    private int pos;

    private Calculator(String s) {
        this.s = s;
    }

    public static BigDecimal evaluate(String expression) throws CalcException {
        Calculator c = new Calculator(expression);
        if (expression.isEmpty()) {
            throw new CalcException("empty", false);
        }
        BigDecimal value = c.parseExpression();
        if (c.pos != c.s.length()) {
            throw new CalcException("unexpected '" + c.s.charAt(c.pos) + "'", false);
        }
        return value;
    }

    /** Formats a result for the display: at most 12 significant digits, ',' separator. */
    public static String format(BigDecimal value) {
        BigDecimal v = value.round(new MathContext(12, RoundingMode.HALF_EVEN));
        if (v.signum() == 0) {
            return "0";
        }
        v = v.stripTrailingZeros();
        int exponent = v.precision() - v.scale() - 1;
        String text;
        if (exponent >= 12 || exponent < -8) {
            String digits = v.unscaledValue().abs().toString();
            String mantissa = digits.length() > 1
                    ? digits.charAt(0) + "." + digits.substring(1)
                    : digits;
            text = (v.signum() < 0 ? "-" : "") + mantissa + "E" + exponent;
        } else {
            text = v.toPlainString();
        }
        return text.replace('.', ',').replace('-', '−');
    }

    private BigDecimal parseExpression() throws CalcException {
        BigDecimal value = parseTerm();
        while (pos < s.length()) {
            char c = s.charAt(pos);
            if (c == '+') {
                pos++;
                value = value.add(parseTerm(), MC);
            } else if (c == '−' || c == '-') {
                pos++;
                value = value.subtract(parseTerm(), MC);
            } else {
                break;
            }
        }
        return value;
    }

    private BigDecimal parseTerm() throws CalcException {
        BigDecimal value = parseUnary();
        while (pos < s.length()) {
            char c = s.charAt(pos);
            if (c == '×' || c == '*') {
                pos++;
                value = value.multiply(parseUnary(), MC);
            } else if (c == '÷' || c == '/') {
                pos++;
                BigDecimal divisor = parseUnary();
                if (divisor.signum() == 0) {
                    throw new CalcException("division by zero", true);
                }
                value = value.divide(divisor, MC);
            } else if (c == '(' || Character.isDigit(c) || c == ',') {
                // Implicit multiplication: 2(3), (2)(3), (2)3
                value = value.multiply(parseUnary(), MC);
            } else {
                break;
            }
        }
        return value;
    }

    private BigDecimal parseUnary() throws CalcException {
        if (pos < s.length()) {
            char c = s.charAt(pos);
            if (c == '−' || c == '-') {
                pos++;
                return parseUnary().negate();
            }
            if (c == '+') {
                pos++;
                return parseUnary();
            }
        }
        return parsePostfix();
    }

    private BigDecimal parsePostfix() throws CalcException {
        BigDecimal value = parsePrimary();
        while (pos < s.length() && s.charAt(pos) == '%') {
            pos++;
            value = value.divide(HUNDRED, MC);
        }
        return value;
    }

    private BigDecimal parsePrimary() throws CalcException {
        if (pos >= s.length()) {
            throw new CalcException("unexpected end", false);
        }
        char c = s.charAt(pos);
        if (c == '(') {
            pos++;
            BigDecimal value = parseExpression();
            if (pos >= s.length() || s.charAt(pos) != ')') {
                throw new CalcException("missing ')'", false);
            }
            pos++;
            return value;
        }
        int start = pos;
        while (pos < s.length() && (Character.isDigit(s.charAt(pos)) || s.charAt(pos) == ',' || s.charAt(pos) == '.')) {
            pos++;
        }
        if (start == pos) {
            throw new CalcException("unexpected '" + c + "'", false);
        }
        String number = s.substring(start, pos).replace(',', '.');
        if (number.equals(".")) {
            throw new CalcException("bad number", false);
        }
        try {
            return new BigDecimal(number);
        } catch (NumberFormatException e) {
            throw new CalcException("bad number " + number, false);
        }
    }
}
