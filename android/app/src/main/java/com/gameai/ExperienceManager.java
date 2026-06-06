package com.gameai;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class ExperienceManager {

    private final File file;
    private JSONArray experiences;

    public ExperienceManager(Context context) {
        file = new File(context.getFilesDir(), "experiences.json");
        experiences = load();
    }

    private JSONArray load() {
        if (!file.exists()) return new JSONArray();
        try {
            BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file)));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            return new JSONArray(sb.toString());
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    private void save() {
        try {
            FileOutputStream fos = new FileOutputStream(file);
            fos.write(experiences.toString().getBytes("UTF-8"));
            fos.close();
        } catch (Exception ignored) {}
    }

    public void add(String goal, String observation, String action) {
        try {
            JSONObject exp = new JSONObject();
            exp.put("id", experiences.length() + 1);
            exp.put("time", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date()));
            exp.put("goal", goal);
            exp.put("observation", observation.length() > 200 ? observation.substring(0, 200) : observation);
            exp.put("action", action.length() > 200 ? action.substring(0, 200) : action);
            experiences.put(exp);

            // Keep only last 50 experiences
            if (experiences.length() > 50) {
                JSONArray trimmed = new JSONArray();
                for (int i = experiences.length() - 50; i < experiences.length(); i++) {
                    trimmed.put(experiences.get(i));
                }
                experiences = trimmed;
            }
            save();
        } catch (JSONException ignored) {}
    }

    public String getRecent(int n) {
        if (experiences.length() == 0) return "";
        StringBuilder sb = new StringBuilder();
        int start = Math.max(0, experiences.length() - n);
        for (int i = start; i < experiences.length(); i++) {
            try {
                JSONObject exp = experiences.getJSONObject(i);
                sb.append("#").append(exp.optInt("id"))
                  .append(" [").append(exp.optString("time")).append("]\n")
                  .append("  观察: ").append(exp.optString("observation")).append("\n")
                  .append("  动作: ").append(exp.optString("action")).append("\n---\n");
            } catch (JSONException ignored) {}
        }
        return sb.toString();
    }
}
