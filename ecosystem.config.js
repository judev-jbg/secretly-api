module.exports = {
  apps: [
    {
      name: "secretly-api",
      script: ".venv/Scripts/uvicorn.exe",
      args: "app.main:app --host 0.0.0.0 --port 8100 --reload",
      interpreter: "none",
      cwd: __dirname,
      env: {
        PORT: 8100,
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
