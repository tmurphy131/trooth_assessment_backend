// Extra T[root]H Armory screens for the onlyblv.com user guide, with the same setup as the app's
// store screenshots (integration_test/screenshots_test.dart in the Armory repo).
//
// Lives in the backend repo (scripts/site/guide_capture/) and is copied into the Armory repo by
// capture_armory.py, which runs it with test_driver/screenshot_driver.dart and removes it again.
import 'dart:io' show Platform;

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:trooth_armory/app.dart';
import 'package:trooth_armory/data/app_database.dart';
import 'package:trooth_armory/screens/category_detail_screen.dart';
import 'package:trooth_armory/screens/personalize_screen.dart';
import 'package:trooth_armory/screens/settings_screen.dart';
import 'package:trooth_armory/services/content_repository.dart';
import 'package:trooth_armory/services/daily_verse_service.dart';
import 'package:trooth_armory/services/link_service.dart';
import 'package:trooth_armory/services/notification_service.dart';
import 'package:trooth_armory/services/remote_config_service.dart';
import 'package:trooth_armory/services/settings_controller.dart';
import 'package:trooth_armory/services/user_data_repository.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('guide screenshots', (tester) async {
    final content = await ContentRepository.load(rootBundle);
    final settings = SettingsController(AppDatabase(NativeDatabase.memory()));
    await settings.load();
    final remoteConfig = await RemoteConfigService.start(
      source: MemoryRemoteConfigSource(),
      defaults: RemoteConfigDefaults.fromJsonString(await rootBundle.loadString(RemoteConfigDefaults.assetPath)),
      categoryIds: content.categories.map((c) => c.id).toSet(),
    );
    final userData = UserDataRepository(settings.database, content);
    await userData.load();

    // A well-known verse on the Today card.
    final probe = DailyVerseService(content, remoteConfig);
    const preferred = ['Joshua 1:9', 'Isaiah 41:10', 'Philippians 4:13', 'Jeremiah 29:11', 'Psalm 46:1'];
    var day = DailyVerseService.startDate;
    for (var i = 0; i < 479 && !preferred.contains(probe.verseFor(day).ref); i++) {
      day = day.add(const Duration(days: 1));
    }
    final dailyVerse = DailyVerseService(content, remoteConfig, clock: () => day);

    // Saved items and a note for the Saved screen.
    for (final id in ['anxiety-worry', 'faith', 'fear-courage']) {
      final s = content.category(id)!.scriptures.first;
      await userData.save(id, SavedSection.scriptures, ref: s.ref, text: s.text);
    }
    await userData.save('peace-joy', SavedSection.takeaway, text: content.category('peace-joy')!.takeaway);
    await userData.toggleFavorite('faith');
    await userData.toggleFavorite('anxiety-worry');
    await userData.saveNote('anxiety-worry', 'Read this before the big meeting. Breathe, pray, and trust Him with the outcome.');

    var surfaceReady = false;
    Future<void> shoot(String name, Widget home, {Future<void> Function()? then}) async {
      await tester.pumpWidget(const SizedBox());
      await tester.pumpWidget(ArmoryApp(
        content: content,
        settings: settings,
        userData: userData,
        remoteConfig: remoteConfig,
        links: LinkService(isReachable: (_) async => true, launch: (_, _) async => true),
        dailyVerse: dailyVerse,
        notifications: NotificationService(settings, _NoNotifications(), openToday: () {}),
        home: home,
      ));
      await tester.pumpAndSettle();
      if (then != null) await then();
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle(const Duration(seconds: 3)); // highlight fades, keyboard hides
      if (Platform.isAndroid && !surfaceReady) {
        // Android draws Flutter to a surface that must be converted once before capturing.
        await binding.convertFlutterSurfaceToImage();
        await tester.pumpAndSettle();
        surfaceReady = true;
      }
      await binding.takeScreenshot(name);
    }

    await shoot('g_options', const CategoryDetailScreen(categoryId: 'anxiety-worry'), then: () async {
      await tester.tap(find.byIcon(Icons.more_horiz).first);
      await tester.pumpAndSettle();
    });
    await shoot('g_personalize', const PersonalizeScreen(categoryId: 'anxiety-worry', ref: 'Matthew 6:25'));
    await shoot('g_settings', const SettingsScreen());
  });
}

class _NoNotifications implements NotificationPlatform {
  @override
  Future<void> initialize(void Function(String? payload) onTap) async {}
  @override
  Future<String?> takeLaunchPayload() async => null;
  @override
  Future<bool> requestPermission() async => false;
  @override
  Future<void> scheduleDaily(ScheduledReminder reminder) async {}
  @override
  Future<void> cancel(int id) async {}
}
