package com.gameai;

import android.app.Activity;
import android.os.Bundle;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(android.view.Gravity.CENTER);

        TextView title = new TextView(this);
        title.setText("GameAI");
        title.setTextSize(32);
        title.setGravity(android.view.Gravity.CENTER);

        TextView subtitle = new TextView(this);
        subtitle.setText("AI Game Assistant");
        subtitle.setTextSize(18);
        subtitle.setGravity(android.view.Gravity.CENTER);

        layout.addView(title);
        layout.addView(subtitle);
        setContentView(layout);
    }
}