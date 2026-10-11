use std::sync::{Arc, Mutex};
use std::process::{Child, Command};
use std::path::PathBuf;
use std::time::Duration;
use std::thread;
use tauri::{AppHandle, Manager};

struct BackendProcess(Arc<Mutex<Option<Child>>>);

/// Find the project root — tries multiple strategies in order.
///
/// Search order:
///   1. $ATTACKGRAPH_ROOT env var (explicit override)
///   2. Working directory (dev: `cargo tauri dev` runs from project root)
///   3. Relative to the AppImage path ($APPIMAGE env var, set by AppImage runtime)
///   4. Walk up from current exe (works for the dev binary in target/)
///   5. XDG data dir fallback: $HOME/.local/share/attackgraph/
fn find_project_root(app: &AppHandle) -> Option<PathBuf> {
    let has_backend = |dir: &PathBuf| dir.join("backend").exists() && dir.join(".venv").exists();

    // 1. Explicit env override
    if let Ok(root) = std::env::var("ATTACKGRAPH_ROOT") {
        let p = PathBuf::from(root);
        if has_backend(&p) {
            return Some(p);
        }
    }

    // 2. Current working directory
    if let Ok(cwd) = std::env::current_dir() {
        if has_backend(&cwd) {
            return Some(cwd);
        }
    }

    // 3. Relative to AppImage path ($APPIMAGE is set by the AppImage runtime)
    if let Ok(appimage) = std::env::var("APPIMAGE") {
        let mut dir = PathBuf::from(appimage);
        dir.pop(); // parent dir of the AppImage file
        for _ in 0..4 {
            if has_backend(&dir) {
                return Some(dir);
            }
            if !dir.pop() { break; }
        }
    }

    // 4. Walk up from exe (works for dev build in target/release/)
    if let Ok(exe) = std::env::current_exe() {
        let mut dir = exe;
        for _ in 0..8 {
            if !dir.pop() { break; }
            if has_backend(&dir) {
                return Some(dir);
            }
        }
    }

    // 5. XDG data dir: ~/.local/share/attackgraph
    let home = std::env::var("HOME").unwrap_or_default();
    if !home.is_empty() {
        let xdg_dir = PathBuf::from(&home).join(".local/share/attackgraph");
        if has_backend(&xdg_dir) {
            return Some(xdg_dir);
        }
        // Also check $HOME/attackgraph (simple deployment)
        let home_dir = PathBuf::from(&home).join("attackgraph");
        if has_backend(&home_dir) {
            return Some(home_dir);
        }
    }

    // 6. Tauri resource dir (bundled sidecar future)
    if let Ok(res) = app.path().resource_dir() {
        for candidate in [
            res.clone(),
            res.parent().map(|p| p.to_path_buf()).unwrap_or_default(),
            res.parent().and_then(|p| p.parent()).map(|p| p.to_path_buf()).unwrap_or_default(),
        ] {
            if has_backend(&candidate) {
                return Some(candidate);
            }
        }
    }

    None
}

/// Start the FastAPI backend. Returns the spawned child process.
fn start_backend(project_root: &PathBuf) -> std::io::Result<Child> {
    let venv_python = project_root.join(".venv/bin/python3");
    let python_bin = if venv_python.exists() {
        venv_python
    } else {
        PathBuf::from("python3")
    };

    Command::new(&python_bin)
        .args([
            "-m", "uvicorn",
            "backend.api.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "warning",
        ])
        .current_dir(project_root)
        .spawn()
}

/// Poll 127.0.0.1:8000 until ready or 30s timeout.
fn wait_for_backend() -> bool {
    for _ in 0..60 {
        thread::sleep(Duration::from_millis(500));
        if std::net::TcpStream::connect_timeout(
            &"127.0.0.1:8000".parse().unwrap(),
            Duration::from_millis(300),
        ).is_ok() {
            return true;
        }
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_handle: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let backend_handle_clone = Arc::clone(&backend_handle);

    tauri::Builder::default()
        .manage(BackendProcess(Arc::clone(&backend_handle)))
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(move |app| {
            let handle = app.handle().clone();

            thread::spawn(move || {
                match find_project_root(&handle) {
                    Some(root) => {
                        log::info!("AttackGraph root: {}", root.display());
                        match start_backend(&root) {
                            Ok(child) => {
                                log::info!("Backend started (pid {})", child.id());
                                *backend_handle_clone.lock().unwrap() = Some(child);
                                if wait_for_backend() {
                                    log::info!("Backend ready on :8000");
                                } else {
                                    log::error!("Backend did not become ready within 30s");
                                }
                            }
                            Err(e) => log::error!("Failed to start backend: {e}"),
                        }
                    }
                    None => {
                        log::error!(
                            "Could not find AttackGraph project root. \
                             Set ATTACKGRAPH_ROOT=/path/to/attackgraph or run from the project directory."
                        );
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            log::info!("Shutting down backend");
                            let _ = child.kill();
                            let _ = child.wait();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running AttackGraph");
}
