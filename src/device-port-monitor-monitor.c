/*
 * Lightweight resident monitor for Device Port Monitor.
 *
 * The settings window remains in Python/GTK, but this always-on process is
 * native C and performs no polling. It wakes only for /dev events and menu
 * interaction.
 */

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <gio/gio.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <unistd.h>

typedef struct _GtkWidget GtkWidget;
typedef struct _AppIndicator AppIndicator;

extern gboolean gtk_init_check(int *argc, char ***argv);
extern void gtk_main(void);
extern void gtk_main_quit(void);
extern GtkWidget *gtk_menu_new(void);
extern GtkWidget *gtk_menu_item_new_with_label(const gchar *label);
extern GtkWidget *gtk_separator_menu_item_new(void);
extern void gtk_menu_shell_append(gpointer menu_shell, GtkWidget *child);
extern void gtk_widget_destroy(GtkWidget *widget);
extern void gtk_widget_set_sensitive(GtkWidget *widget, gboolean sensitive);
extern void gtk_widget_show_all(GtkWidget *widget);

extern AppIndicator *app_indicator_new(
    const gchar *id, const gchar *icon_name, gint category);
extern void app_indicator_set_icon_full(
    AppIndicator *self, const gchar *icon_name, const gchar *icon_desc);
extern void app_indicator_set_icon_theme_path(
    AppIndicator *self, const gchar *icon_theme_path);
extern void app_indicator_set_label(
    AppIndicator *self, const gchar *label, const gchar *guide);
extern void app_indicator_set_menu(AppIndicator *self, GtkWidget *menu);
extern void app_indicator_set_status(AppIndicator *self, gint status);
extern void app_indicator_set_title(AppIndicator *self, const gchar *title);

#define APP_INDICATOR_CATEGORY_HARDWARE 3
#define APP_INDICATOR_STATUS_ACTIVE 1
#define DEBOUNCE_MS 300

typedef struct {
    GPtrArray *all;
    GPtrArray *acm;
    GPtrArray *usb;
    GPtrArray *video;
} DeviceLists;

typedef struct {
    DeviceLists *devices;
    GFileMonitor *file_monitor;
    guint refresh_source;
    AppIndicator *indicator;
    GtkWidget *menu;
    gchar *icon_path;
    gchar *icon_directory;
    gint lock_fd;
} MonitorApp;

static gint string_pointer_compare(gconstpointer left, gconstpointer right) {
    const gchar *left_string = *(gchar *const *)left;
    const gchar *right_string = *(gchar *const *)right;
    return g_strcmp0(left_string, right_string);
}

static gboolean is_watched_name(const gchar *name) {
    return g_str_has_prefix(name, "ttyACM") ||
           g_str_has_prefix(name, "ttyUSB") ||
           g_str_has_prefix(name, "video");
}

static DeviceLists *device_lists_new(void) {
    DeviceLists *lists = g_new0(DeviceLists, 1);
    lists->all = g_ptr_array_new_with_free_func(g_free);
    lists->acm = g_ptr_array_new();
    lists->usb = g_ptr_array_new();
    lists->video = g_ptr_array_new();
    return lists;
}

static void device_lists_free(DeviceLists *lists) {
    if (lists == NULL) {
        return;
    }
    g_ptr_array_free(lists->acm, TRUE);
    g_ptr_array_free(lists->usb, TRUE);
    g_ptr_array_free(lists->video, TRUE);
    g_ptr_array_free(lists->all, TRUE);
    g_free(lists);
}

static DeviceLists *scan_devices(void) {
    DeviceLists *lists = device_lists_new();
    DIR *directory = opendir("/dev");
    if (directory == NULL) {
        g_printerr("Unable to scan /dev: %s\n", g_strerror(errno));
        return lists;
    }

    struct dirent *entry;
    while ((entry = readdir(directory)) != NULL) {
        if (!is_watched_name(entry->d_name)) {
            continue;
        }
        gchar *path = g_strconcat("/dev/", entry->d_name, NULL);
        g_ptr_array_add(lists->all, path);
        if (g_str_has_prefix(entry->d_name, "ttyACM")) {
            g_ptr_array_add(lists->acm, path);
        } else if (g_str_has_prefix(entry->d_name, "ttyUSB")) {
            g_ptr_array_add(lists->usb, path);
        } else {
            g_ptr_array_add(lists->video, path);
        }
    }
    closedir(directory);

    g_ptr_array_sort(lists->all, string_pointer_compare);
    g_ptr_array_sort(lists->acm, string_pointer_compare);
    g_ptr_array_sort(lists->usb, string_pointer_compare);
    g_ptr_array_sort(lists->video, string_pointer_compare);
    return lists;
}

static gboolean device_lists_equal(
    const DeviceLists *left, const DeviceLists *right) {
    if (left->all->len != right->all->len) {
        return FALSE;
    }
    for (guint index = 0; index < left->all->len; ++index) {
        if (g_strcmp0(
                g_ptr_array_index(left->all, index),
                g_ptr_array_index(right->all, index)) != 0) {
            return FALSE;
        }
    }
    return TRUE;
}

static gboolean contains_path(const GPtrArray *paths, const gchar *path) {
    for (guint index = 0; index < paths->len; ++index) {
        if (g_strcmp0(g_ptr_array_index(paths, index), path) == 0) {
            return TRUE;
        }
    }
    return FALSE;
}

static gchar *find_icon_path(void) {
    const gchar *data_home = g_get_user_data_dir();
    gchar *persistent = g_build_filename(
        data_home, "icons", "hicolor", "256x256", "apps",
        "device-port-monitor.png", NULL);
    if (g_file_test(persistent, G_FILE_TEST_IS_REGULAR)) {
        return persistent;
    }
    g_free(persistent);

    const gchar *appdir = g_getenv("APPDIR");
    if (appdir != NULL && *appdir != '\0') {
        gchar *bundled = g_build_filename(
            appdir, "device-port-monitor.png", NULL);
        if (g_file_test(bundled, G_FILE_TEST_IS_REGULAR)) {
            return bundled;
        }
        g_free(bundled);
    }

    if (g_file_test(
            "/usr/share/pixmaps/device-port-monitor.png",
            G_FILE_TEST_IS_REGULAR)) {
        return g_strdup("/usr/share/pixmaps/device-port-monitor.png");
    }
    return NULL;
}

static void child_exited(GPid process_id, gint status, gpointer user_data) {
    (void)status;
    (void)user_data;
    g_spawn_close_pid(process_id);
}

static void spawn_nonblocking(gchar **arguments) {
    GError *error = NULL;
    GPid process_id = 0;
    if (!g_spawn_async(
            NULL,
            arguments,
            NULL,
            G_SPAWN_SEARCH_PATH | G_SPAWN_DO_NOT_REAP_CHILD,
            NULL,
            NULL,
            &process_id,
            &error)) {
        g_printerr("Unable to start %s: %s\n", arguments[0], error->message);
        g_error_free(error);
        return;
    }
    g_child_watch_add(process_id, child_exited, NULL);
}

static void play_device_sound(gboolean has_added, gboolean has_removed) {
    const gchar *sound_id = "message";
    const gchar *description = "Device configuration changed";
    if (has_added && !has_removed) {
        sound_id = "device-added";
        description = "Device connected";
    } else if (has_removed && !has_added) {
        sound_id = "device-removed";
        description = "Device disconnected";
    }

    gchar *sound_argument = g_strdup_printf("--id=%s", sound_id);
    gchar *description_argument = g_strdup_printf(
        "--description=%s", description);
    gchar *arguments[] = {
        "canberra-gtk-play",
        sound_argument,
        description_argument,
        "--cache-control=permanent",
        NULL,
    };
    spawn_nonblocking(arguments);
    g_free(description_argument);
    g_free(sound_argument);
}

static void send_notification(
    const DeviceLists *previous,
    const DeviceLists *current,
    const gchar *icon_path) {
    GString *body = g_string_new(NULL);
    gboolean has_added = FALSE;
    gboolean has_removed = FALSE;

    for (guint index = 0; index < current->all->len; ++index) {
        const gchar *path = g_ptr_array_index(current->all, index);
        if (!contains_path(previous->all, path)) {
            if (!has_added) {
                g_string_append(body, "Connected:\n");
            }
            g_string_append_printf(body, "%s\n", path);
            has_added = TRUE;
        }
    }
    for (guint index = 0; index < previous->all->len; ++index) {
        const gchar *path = g_ptr_array_index(previous->all, index);
        if (!contains_path(current->all, path)) {
            if (body->len > 0) {
                g_string_append_c(body, '\n');
            }
            if (!has_removed) {
                g_string_append(body, "Disconnected:\n");
            }
            g_string_append_printf(body, "%s\n", path);
            has_removed = TRUE;
        }
    }

    const gchar *title = "Device configuration changed";
    if (has_added && !has_removed) {
        title = "Device connected";
    } else if (has_removed && !has_added) {
        title = "Device disconnected";
    }

    gchar *icon_argument = g_strdup_printf(
        "--icon=%s",
        icon_path != NULL ? icon_path : "drive-removable-media-symbolic");
    gchar *arguments[] = {
        "notify-send",
        "--app-name=Device Port Monitor",
        "--expire-time=5000",
        icon_argument,
        (gchar *)title,
        body->str,
        NULL,
    };
    spawn_nonblocking(arguments);
    play_device_sound(has_added, has_removed);
    g_free(icon_argument);
    g_string_free(body, TRUE);
}

static void append_disabled_item(GtkWidget *menu, const gchar *label) {
    GtkWidget *item = gtk_menu_item_new_with_label(label);
    gtk_widget_set_sensitive(item, FALSE);
    gtk_menu_shell_append(menu, item);
}

static void append_separator(GtkWidget *menu) {
    gtk_menu_shell_append(menu, gtk_separator_menu_item_new());
}

static void append_device_section(
    GtkWidget *menu, const gchar *title, const GPtrArray *paths) {
    append_disabled_item(menu, title);
    if (paths->len == 0) {
        append_disabled_item(menu, "  (none)");
        return;
    }
    for (guint index = 0; index < paths->len; ++index) {
        const gchar *path = g_ptr_array_index(paths, index);
        gchar *label = g_strdup_printf("  %s", path);
        append_disabled_item(menu, label);
        g_free(label);
    }
}

static void settings_activated(
    GtkWidget *item, gpointer user_data) {
    (void)item;
    (void)user_data;
    const gchar *appimage = g_getenv("APPIMAGE");
    gchar *arguments[] = {
        (gchar *)((appimage != NULL && *appimage != '\0')
                      ? appimage
                      : "/usr/bin/device-port-monitor"),
        "--settings",
        NULL,
    };
    spawn_nonblocking(arguments);
}

static void quit_activated(GtkWidget *item, gpointer user_data) {
    (void)item;
    (void)user_data;
    gtk_main_quit();
}

static void render_menu(MonitorApp *app) {
    DeviceLists *devices = app->devices;
    GtkWidget *new_menu = gtk_menu_new();
    gchar *summary = g_strdup_printf(
        "ACM %u / USB %u / VIDEO %u",
        devices->acm->len,
        devices->usb->len,
        devices->video->len);
    append_disabled_item(new_menu, summary);
    g_free(summary);

    append_separator(new_menu);
    append_device_section(new_menu, "ACM ports", devices->acm);
    append_separator(new_menu);
    append_device_section(new_menu, "USB serial ports", devices->usb);
    append_separator(new_menu);
    append_device_section(new_menu, "Video devices", devices->video);
    append_separator(new_menu);

    GtkWidget *settings = gtk_menu_item_new_with_label("Settings");
    g_signal_connect_data(
        settings,
        "activate",
        G_CALLBACK(settings_activated),
        app,
        NULL,
        0);
    gtk_menu_shell_append(new_menu, settings);

    GtkWidget *quit = gtk_menu_item_new_with_label("Quit");
    g_signal_connect_data(
        quit, "activate", G_CALLBACK(quit_activated), app, NULL, 0);
    gtk_menu_shell_append(new_menu, quit);

    gchar *label = g_strdup_printf(
        "ACM %u · USB %u · VID %u",
        devices->acm->len,
        devices->usb->len,
        devices->video->len);
    app_indicator_set_label(
        app->indicator, label, "ACM 99 · USB 99 · VID 99");
    g_free(label);

    GtkWidget *old_menu = app->menu;
    app->menu = new_menu;
    app_indicator_set_menu(app->indicator, new_menu);
    gtk_widget_show_all(new_menu);
    if (old_menu != NULL) {
        gtk_widget_destroy(old_menu);
    }
}

static gboolean refresh_devices(gpointer user_data) {
    MonitorApp *app = user_data;
    app->refresh_source = 0;
    DeviceLists *current = scan_devices();
    if (device_lists_equal(app->devices, current)) {
        device_lists_free(current);
        return G_SOURCE_REMOVE;
    }

    DeviceLists *previous = app->devices;
    app->devices = current;
    render_menu(app);
    send_notification(previous, current, app->icon_path);
    device_lists_free(previous);
    return G_SOURCE_REMOVE;
}

static void dev_directory_changed(
    GFileMonitor *monitor,
    GFile *file,
    GFile *other_file,
    GFileMonitorEvent event_type,
    gpointer user_data) {
    (void)monitor;
    (void)other_file;
    (void)event_type;
    MonitorApp *app = user_data;
    gchar *name = file != NULL ? g_file_get_basename(file) : NULL;
    if (name == NULL || !is_watched_name(name)) {
        g_free(name);
        return;
    }
    g_free(name);

    if (app->refresh_source != 0) {
        g_source_remove(app->refresh_source);
    }
    app->refresh_source = g_timeout_add(DEBOUNCE_MS, refresh_devices, app);
}

static gint acquire_instance_lock(void) {
    const gchar *runtime_directory = g_get_user_runtime_dir();
    gchar *path = g_build_filename(
        runtime_directory, "device-port-monitor.lock", NULL);
    gint descriptor = open(path, O_CREAT | O_RDWR, 0600);
    g_free(path);
    if (descriptor < 0) {
        g_printerr("Unable to open the instance lock: %s\n", g_strerror(errno));
        return -1;
    }
    if (flock(descriptor, LOCK_EX | LOCK_NB) != 0) {
        g_printerr("Device Port Monitor is already running.\n");
        close(descriptor);
        return -1;
    }
    return descriptor;
}

static void print_status(void) {
    DeviceLists *devices = scan_devices();
    for (guint index = 0; index < devices->all->len; ++index) {
        g_print("%s\n", (gchar *)g_ptr_array_index(devices->all, index));
    }
    device_lists_free(devices);
}

int main(int argc, char **argv) {
    if (argc > 1 && g_strcmp0(argv[1], "--print-status") == 0) {
        print_status();
        return 0;
    }

    MonitorApp app = {0};
    app.lock_fd = acquire_instance_lock();
    if (app.lock_fd < 0) {
        return 0;
    }
    if (!gtk_init_check(&argc, &argv)) {
        g_printerr("Unable to initialize GTK.\n");
        close(app.lock_fd);
        return 1;
    }

    app.icon_path = find_icon_path();
    app.icon_directory = app.icon_path != NULL
                             ? g_path_get_dirname(app.icon_path)
                             : NULL;
    const gchar *icon_name = app.icon_path != NULL
                                 ? "device-port-monitor"
                                 : "drive-removable-media-symbolic";
    app.indicator = app_indicator_new(
        "device-port-monitor", icon_name, APP_INDICATOR_CATEGORY_HARDWARE);
    if (app.icon_directory != NULL) {
        app_indicator_set_icon_theme_path(app.indicator, app.icon_directory);
        app_indicator_set_icon_full(
            app.indicator, icon_name, "Device Port Monitor");
    }
    app_indicator_set_title(app.indicator, "Device Port Monitor");
    app_indicator_set_status(app.indicator, APP_INDICATOR_STATUS_ACTIVE);

    app.devices = scan_devices();
    render_menu(&app);

    GError *error = NULL;
    GFile *dev_directory = g_file_new_for_path("/dev");
    app.file_monitor = g_file_monitor_directory(
        dev_directory, G_FILE_MONITOR_NONE, NULL, &error);
    g_object_unref(dev_directory);
    if (app.file_monitor == NULL) {
        g_printerr("Unable to monitor /dev: %s\n", error->message);
        g_error_free(error);
        device_lists_free(app.devices);
        gtk_widget_destroy(app.menu);
        g_object_unref(app.indicator);
        g_free(app.icon_directory);
        g_free(app.icon_path);
        close(app.lock_fd);
        return 1;
    }
    g_signal_connect(
        app.file_monitor,
        "changed",
        G_CALLBACK(dev_directory_changed),
        &app);

    gtk_main();

    if (app.refresh_source != 0) {
        g_source_remove(app.refresh_source);
    }
    g_file_monitor_cancel(app.file_monitor);
    g_object_unref(app.file_monitor);
    gtk_widget_destroy(app.menu);
    g_object_unref(app.indicator);
    device_lists_free(app.devices);
    g_free(app.icon_directory);
    g_free(app.icon_path);
    close(app.lock_fd);
    return 0;
}
