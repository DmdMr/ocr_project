#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Mutex, MutexGuard};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent};

const DEFAULT_BACKEND_HOST: &str = "127.0.0.1";
const DEFAULT_BACKEND_PORT: u16 = 8000;
const BACKEND_WAIT_TIMEOUT_SECS: u64 = 20;

#[derive(Default)]
struct BackendProcessState {
    child: Mutex<Option<Child>>,
}

impl BackendProcessState {
    fn lock_child(&self) -> MutexGuard<'_, Option<Child>> {
        self.child.lock().expect("backend process mutex poisoned")
    }
}

fn project_root_dir() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .map(PathBuf::from)
        .unwrap_or(manifest_dir)
}

fn parse_command(raw: &str) -> Option<(String, Vec<String>)> {
    let parts = shell_words::split(raw).ok()?;
    let (program, args) = parts.split_first()?;
    Some((program.to_owned(), args.to_vec()))
}

fn backend_command() -> (String, Vec<String>) {
    if let Ok(raw) = std::env::var("OCR_BACKEND_CMD") {
        if let Some(parsed) = parse_command(&raw) {
            return parsed;
        }
    }

    (
        "python".to_string(),
        vec![
            "-m".to_string(),
            "uvicorn".to_string(),
            "backend.app.main:app".to_string(),
            "--host".to_string(),
            DEFAULT_BACKEND_HOST.to_string(),
            "--port".to_string(),
            DEFAULT_BACKEND_PORT.to_string(),
        ],
    )
}

fn backend_is_reachable() -> bool {
    let addr: SocketAddr = format!("{}:{}", DEFAULT_BACKEND_HOST, DEFAULT_BACKEND_PORT)
        .parse()
        .expect("invalid backend socket address");

    TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok()
}

fn wait_for_backend() -> bool {
    let timeout = Duration::from_secs(BACKEND_WAIT_TIMEOUT_SECS);
    let start = Instant::now();

    while start.elapsed() <= timeout {
        if backend_is_reachable() {
            return true;
        }
        thread::sleep(Duration::from_millis(300));
    }

    false
}

fn spawn_backend_if_needed() -> Option<Child> {
    if backend_is_reachable() {
        return None;
    }

    let (program, args) = backend_command();
    let mut command = Command::new(program);
    command
        .args(args)
        .current_dir(project_root_dir())
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());

    command.spawn().ok()
}

fn stop_backend_if_owned(app: &AppHandle) {
    let state = app.state::<BackendProcessState>();
    let mut child_slot = state.lock_child();
    if let Some(child) = child_slot.as_mut() {
        let _ = child.kill();
        let _ = child.wait();
    }
    *child_slot = None;
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(BackendProcessState::default());

            let backend_child = spawn_backend_if_needed();
            if let Some(child) = backend_child {
                let state = app.state::<BackendProcessState>();
                let mut slot = state.lock_child();
                *slot = Some(child);
            }

            let _ = wait_for_backend();

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
                stop_backend_if_owned(app);
            }
        });
}
