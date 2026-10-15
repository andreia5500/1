package com.andreia.calculator;

import android.app.Activity;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

public class MainActivity extends Activity {

    private static final String KEY_EXPRESSION = "expression";
    private static final String KEY_EVALUATED = "evaluated";
    private static final int MAX_LENGTH = 100;

    private TextView expressionView;
    private TextView resultView;
    private Button clearButton;

    private final StringBuilder expression = new StringBuilder();
    /** True right after '=': the next digit starts a new expression. */
    private boolean justEvaluated;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        expressionView = (TextView) findViewById(R.id.expression);
        resultView = (TextView) findViewById(R.id.result);
        clearButton = (Button) findViewById(R.id.btn_clear);

        findViewById(R.id.btn_back).setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                v.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
                clearAll();
                return true;
            }
        });

        if (savedInstanceState != null) {
            expression.append(savedInstanceState.getString(KEY_EXPRESSION, ""));
            justEvaluated = savedInstanceState.getBoolean(KEY_EVALUATED, false);
        }
        refresh();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putString(KEY_EXPRESSION, expression.toString());
        outState.putBoolean(KEY_EVALUATED, justEvaluated);
    }

    /** Click handler for every button, wired through android:onClick in the layout. */
    public void onButton(View view) {
        view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
        String key = ((Button) view).getText().toString();
        switch (key) {
            case "AC":
            case "C":
                clearAll();
                return;
            case "⌫":
                backspace();
                break;
            case "=":
                equals();
                return;
            case "( )":
                parenthesis();
                break;
            case ",":
                decimalPoint();
                break;
            case "%":
                percent();
                break;
            case "+":
            case "−":
            case "×":
            case "÷":
                operator(key.charAt(0));
                break;
            default:
                digit(key.charAt(0));
                break;
        }
        refresh();
    }

    private void clearAll() {
        expression.setLength(0);
        justEvaluated = false;
        refresh();
    }

    private void backspace() {
        justEvaluated = false;
        if (expression.length() > 0) {
            expression.setLength(expression.length() - 1);
        }
    }

    private void digit(char d) {
        if (justEvaluated) {
            expression.setLength(0);
            justEvaluated = false;
        }
        if (expression.length() >= MAX_LENGTH) {
            return;
        }
        char last = lastChar();
        if (last == ')' || last == '%') {
            expression.append('×');
        }
        // Replace a lone leading zero: "0" + "5" -> "5", but keep "0,"
        String number = currentNumber();
        if (number.equals("0")) {
            expression.setLength(expression.length() - 1);
        }
        expression.append(d);
    }

    private void decimalPoint() {
        if (justEvaluated) {
            expression.setLength(0);
            justEvaluated = false;
        }
        if (currentNumber().indexOf(',') >= 0) {
            return;
        }
        char last = lastChar();
        if (last == ')' || last == '%') {
            expression.append('×');
        }
        if (!Character.isDigit(lastChar())) {
            expression.append('0');
        }
        expression.append(',');
    }

    private void operator(char op) {
        justEvaluated = false;
        char last = lastChar();
        if (expression.length() == 0 || last == '(') {
            // Only a leading minus makes sense here.
            if (op == '−') {
                expression.append(op);
            }
            return;
        }
        if (isOperator(last)) {
            // "5×−" is fine; otherwise replace the previous operator.
            if (op == '−' && (last == '×' || last == '÷')) {
                expression.append(op);
                return;
            }
            expression.setLength(expression.length() - 1);
            // Also drop a minus that followed × or ÷: "5×−" + "+" -> "5+"
            if (isOperator(lastChar())) {
                expression.setLength(expression.length() - 1);
            }
            if (expression.length() == 0 || lastChar() == '(') {
                if (op == '−') {
                    expression.append(op);
                }
                return;
            }
        } else if (last == ',') {
            expression.append('0');
        }
        expression.append(op);
    }

    private void percent() {
        justEvaluated = false;
        char last = lastChar();
        if (Character.isDigit(last) || last == ')') {
            expression.append('%');
        }
    }

    private void parenthesis() {
        justEvaluated = false;
        int open = 0;
        for (int i = 0; i < expression.length(); i++) {
            char c = expression.charAt(i);
            if (c == '(') open++;
            if (c == ')') open--;
        }
        char last = lastChar();
        boolean afterValue = Character.isDigit(last) || last == ')' || last == '%' || last == ',';
        if (open > 0 && afterValue) {
            expression.append(')');
        } else {
            if (afterValue) {
                expression.append('×');
            }
            expression.append('(');
        }
    }

    private void equals() {
        if (expression.length() == 0) {
            return;
        }
        try {
            BigDecimal value = Calculator.evaluate(completed(expression.toString()));
            expression.setLength(0);
            expression.append(toEditable(value));
            justEvaluated = true;
            refresh();
        } catch (Calculator.CalcException e) {
            resultView.setTextColor(getResources().getColor(R.color.error));
            resultView.setText(e.divisionByZero ? R.string.err_div_zero : R.string.err_syntax);
        }
    }

    /** Updates the display and the live preview of the result. */
    private void refresh() {
        String text = expression.toString();
        expressionView.setText(text.isEmpty() ? "0" : text);
        float size = text.length() <= 8 ? 56 : text.length() <= 12 ? 44 : text.length() <= 16 ? 36 : 28;
        expressionView.setTextSize(TypedValue.COMPLEX_UNIT_SP, size);
        clearButton.setText(text.isEmpty() ? "AC" : "C");

        resultView.setTextColor(getResources().getColor(R.color.text_dim));
        resultView.setText("");
        if (justEvaluated || !hasOperation(text)) {
            return;
        }
        try {
            BigDecimal value = Calculator.evaluate(completed(text));
            resultView.setText("= " + Calculator.format(value));
        } catch (Calculator.CalcException ignored) {
            // Incomplete input: no preview.
        }
    }

    /** Drops a trailing operator and closes open parentheses, so "2×(3+" previews as "2×(3)". */
    private static String completed(String text) {
        StringBuilder b = new StringBuilder(text);
        while (b.length() > 0) {
            char last = b.charAt(b.length() - 1);
            if (isOperator(last) || last == '(') {
                b.setLength(b.length() - 1);
            } else {
                break;
            }
        }
        int open = 0;
        for (int i = 0; i < b.length(); i++) {
            if (b.charAt(i) == '(') open++;
            if (b.charAt(i) == ')') open--;
        }
        for (; open > 0; open--) {
            b.append(')');
        }
        return b.toString();
    }

    /** A result in a form that can be edited further (no exponent notation). */
    private static String toEditable(BigDecimal value) {
        String formatted = Calculator.format(value);
        if (formatted.indexOf('E') < 0) {
            return formatted;
        }
        BigDecimal rounded = value.round(new MathContext(12, RoundingMode.HALF_EVEN)).stripTrailingZeros();
        return rounded.toPlainString().replace('.', ',').replace('-', '−');
    }

    private static boolean hasOperation(String text) {
        for (int i = 1; i < text.length(); i++) {
            char c = text.charAt(i);
            if (isOperator(c) || c == '%' || c == '(' || c == ')') {
                return true;
            }
        }
        return text.indexOf('%') >= 0 || text.indexOf('(') >= 0;
    }

    private static boolean isOperator(char c) {
        return c == '+' || c == '−' || c == '×' || c == '÷';
    }

    private char lastChar() {
        return expression.length() == 0 ? 0 : expression.charAt(expression.length() - 1);
    }

    /** The digits and comma of the number at the end of the expression. */
    private String currentNumber() {
        int i = expression.length();
        while (i > 0 && (Character.isDigit(expression.charAt(i - 1)) || expression.charAt(i - 1) == ',')) {
            i--;
        }
        return expression.substring(i);
    }
}
