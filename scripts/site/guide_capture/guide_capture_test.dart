// Screenshot harness for the onlyblv.com user guides (T[root]H Discipleship).
//
// Lives in the backend repo (scripts/site/guide_capture/) and is copied into the Flutter
// repo's integration_test/ by capture.py, which runs it and removes it again. It drives the
// real app against DEV with the guide test accounts and prints CAPTURE:<name> at each shot;
// capture.py answers with `xcrun simctl io <sim> screenshot`.
//
// Dart defines (capture.py passes these):
//   STAGE=a   screens that need the pending invite and an unsubmitted draft (run right after seeding)
//   STAGE=b   everything else (after seed_data.py has accepted the invite and submitted work)
//   TIER=free|premium   suffix for report/subscription shots, to match the accounts' current plan
//   ONLY=name,name      run only these steps (step names, not shot names)
//   MENTOR_EMAIL, MENTOR_PASSWORD, APPRENTICE_EMAIL, APPRENTICE_PASSWORD

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trooth_assessment/main.dart' as app;
import 'package:trooth_assessment/screens/apprentice_dashboard_new.dart';
import 'package:trooth_assessment/screens/apprentice_invite_screen.dart';
import 'package:trooth_assessment/screens/auth_gate.dart';
import 'package:trooth_assessment/screens/mentor_dashboard_new.dart';
import 'package:trooth_assessment/screens/mentor_gift_seats_screen.dart';
import 'package:trooth_assessment/screens/simple_login_screen.dart';
import 'package:trooth_assessment/screens/subscription_screen.dart';
import 'package:trooth_assessment/services/api_service.dart';
import 'package:trooth_assessment/utils/logout_util.dart';

const stage = String.fromEnvironment('STAGE', defaultValue: 'a');
const mentorEmail = String.fromEnvironment('MENTOR_EMAIL');
const mentorPassword = String.fromEnvironment('MENTOR_PASSWORD');
const apprenticeEmail = String.fromEnvironment('APPRENTICE_EMAIL');
const apprenticePassword = String.fromEnvironment('APPRENTICE_PASSWORD');
const only = String.fromEnvironment('ONLY'); // comma list of step names to run
const tier = String.fromEnvironment('TIER', defaultValue: 'free'); // suffix for report shots

Future<void> pumpFor(WidgetTester tester, double seconds) async {
  final end = DateTime.now().add(Duration(milliseconds: (seconds * 1000).round()));
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

Future<void> pumpUntil(WidgetTester tester, Finder finder, {double timeout = 45}) async {
  final end = DateTime.now().add(Duration(milliseconds: (timeout * 1000).round()));
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 250));
    if (finder.evaluate().isNotEmpty) return;
  }
  throw TestFailure('Timed out waiting for $finder');
}

/// Let network loads finish, then hold still while the host takes the screenshot.
Future<void> shot(WidgetTester tester, String name, {double settle = 4}) async {
  await pumpFor(tester, settle);
  // ignore: avoid_print
  print('CAPTURE:$name');
  await pumpFor(tester, 2.5);
}

var _pointer = 1000;

/// Device-sourced tap so the test framework's tap crosshair never shows in shots.
Future<void> tap(WidgetTester tester, Finder finder) async {
  // Prefer an on-screen match: TabBarView keeps other tabs built, and ensureVisible
  // on an offstage match would scroll the tab view to it.
  final visible = finder.hitTestable();
  if (visible.evaluate().isNotEmpty) {
    finder = visible;
  } else {
    final width = tester.view.physicalSize.width / tester.view.devicePixelRatio;
    final onScreen = finder.evaluate().where((e) {
      final box = e.renderObject;
      if (box is! RenderBox || !box.hasSize || !box.attached) return false;
      final x = box.localToGlobal(box.size.center(Offset.zero)).dx;
      return x >= 0 && x <= width;
    }).toSet();
    if (onScreen.isNotEmpty) {
      // Already visible; take its position now (the screen may rebuild these elements)
      return _tapAt(tester, tester.getCenter(find.byElementPredicate(onScreen.contains).first));
    }
  }
  await tester.ensureVisible(finder.first);
  await tester.pump(const Duration(milliseconds: 300));
  await _tapAt(tester, tester.getCenter(finder.first));
}

Future<void> _tapAt(WidgetTester tester, Offset at) async {
  final binding = tester.binding as LiveTestWidgetsFlutterBinding;
  final id = ++_pointer;
  binding.handlePointerEventForSource(PointerDownEvent(pointer: id, position: at), source: TestBindingEventSource.device);
  await tester.pump(const Duration(milliseconds: 60));
  binding.handlePointerEventForSource(PointerUpEvent(pointer: id, position: at), source: TestBindingEventSource.device);
  await tester.pump();
}

Future<void> back(WidgetTester tester) async {
  final nav = tester.state<NavigatorState>(find.byType(Navigator).last);
  nav.pop();
  await pumpFor(tester, 1.2);
}

Future<void> quietFirstRun() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool('tutorial_shown_apprentice_dashboard_v1', true);
  await prefs.setBool('tutorial_shown_mentor_dashboard_v1', true);
  await prefs.setString('notification_primer_snoozed_until', DateTime.now().add(const Duration(days: 30)).toIso8601String());
}

Future<void> clearOverlays(WidgetTester tester) async {
  for (final label in ['SKIP', 'Not now', 'Maybe later', 'Later']) {
    final f = find.text(label);
    if (f.evaluate().isNotEmpty) {
      await tap(tester, f);
      await pumpFor(tester, 0.8);
    }
  }
}

Future<void> signIn(WidgetTester tester, String email, String password) async {
  await pumpUntil(tester, find.byType(SimpleLoginScreen));
  await pumpFor(tester, 1);
  final fields = find.byType(TextFormField);
  await tester.enterText(fields.at(0), email);
  await tester.enterText(fields.at(1), password);
  FocusManager.instance.primaryFocus?.unfocus();
  await pumpFor(tester, 0.6);
  await tap(tester, find.text('Sign In'));
}

Future<void> signOut(WidgetTester tester) async {
  await signOutEverywhere();
  await pumpUntil(tester, find.byType(SimpleLoginScreen));
  await pumpFor(tester, 1);
}

/// Runs [body] unless ONLY is set and doesn't include [name]. Failures are logged, not fatal,
/// and the navigator is popped back to [home] so the next shot starts clean.
Future<void> step(WidgetTester tester, String name, Type home, Future<void> Function() body) async {
  if (only.isNotEmpty && !only.split(',').contains(name)) return;
  try {
    await body();
  } catch (e, st) {
    // ignore: avoid_print
    print('SHOTFAIL:$name $e');
    // ignore: avoid_print
    print('SHOTSTACK:${st.toString().split('\n').where((l) => l.contains('guide_capture')).take(3).join(' | ')}');
  }
  final nav = find.byType(Navigator);
  for (var i = 0; i < 6 && find.byType(home).hitTestable().evaluate().isEmpty; i++) {
    if (nav.evaluate().isEmpty) break;
    tester.state<NavigatorState>(nav.last).maybePop();
    await pumpFor(tester, 0.8);
  }
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  binding.shouldPropagateDevicePointerEvents = true;

  testWidgets('guide capture stage $stage', (tester) async {
    final testErrorHandler = FlutterError.onError;
    final testErrorWidgetBuilder = ErrorWidget.builder;
    await quietFirstRun();
    // Same dev backend via its Cloud Run URL, so the "-dev." DEV corner banner stays out of the shots.
    ApiService().baseUrlOverride = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app';
    app.main();
    final authGate = find.byType(AuthGate);
    final login = find.byType(SimpleLoginScreen);
    await pumpUntil(tester, find.byWidgetPredicate((_) => authGate.evaluate().isNotEmpty || login.evaluate().isNotEmpty));
    FlutterError.onError = testErrorHandler;
    if (FirebaseAuth.instance.currentUser != null) await signOut(tester);

    if (stage == 'a') {
      // Sign-up screen for "Getting started"
      await pumpFor(tester, 1);
      await tap(tester, find.textContaining('Sign up'));
      await pumpFor(tester, 1.5);
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), 'Jordan');
      await tester.enterText(fields.at(1), 'Davis');
      FocusManager.instance.primaryFocus?.unfocus();
      await pumpFor(tester, 0.6);
      await tap(tester, find.text('Apprentice'));
      await shot(tester, 'signup', settle: 1);
      await back(tester);

      await signIn(tester, apprenticeEmail, apprenticePassword);
      await pumpUntil(tester, find.byType(ApprenticeDashboardNew));
      await pumpFor(tester, 3);
      await clearOverlays(tester);
      await shot(tester, 'apprentice_dashboard_draft', settle: 5);

      await step(tester, 'apprentice_invites', ApprenticeDashboardNew, () async {
        await tap(tester, find.byTooltip('Invitations'));
        await shot(tester, 'apprentice_invites');
      });

      await step(tester, 'apprentice_assessment', ApprenticeDashboardNew, () async {
        await tap(tester, find.textContaining('Master').first);
        await pumpFor(tester, 2);
        // Some flows show a "resume?" dialog first
        for (final l in ['Resume', 'Continue', 'Start']) {
          if (find.text(l).evaluate().isNotEmpty) {
            await tap(tester, find.text(l));
            break;
          }
        }
        await shot(tester, 'apprentice_assessment', settle: 5);
      });

      await step(tester, 'apprentice_new_assessment', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('New Assessment'));
        await shot(tester, 'apprentice_new_assessment', settle: 3);
      });

      await step(tester, 'gifts_assessment', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('Spiritual Gifts'));
        await pumpFor(tester, 1.5);
        await shot(tester, 'gifts_disclaimer', settle: 0.5);
        await tap(tester, find.text('Begin'));
        await shot(tester, 'gifts_assessment', settle: 4);
      });

      await signOut(tester);
    }

    if (stage == 'b') {
      // ---------- Apprentice ----------
      await signIn(tester, apprenticeEmail, apprenticePassword);
      await pumpUntil(tester, find.byType(ApprenticeDashboardNew));
      await pumpFor(tester, 3);
      await clearOverlays(tester);
      await step(tester, 'apprentice_dashboard', ApprenticeDashboardNew, () async {
        await shot(tester, 'apprentice_dashboard', settle: 5);
      });

      await step(tester, 'apprentice_report', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('View Progress'));
        await pumpFor(tester, 3);
        await tap(tester, find.textContaining('Master').last);
        await pumpUntil(tester, find.byType(CircularProgressIndicator), timeout: 5).catchError((_) {});
        for (var i = 0; i < 120 && find.byType(CircularProgressIndicator).evaluate().isNotEmpty; i++) {
          await pumpFor(tester, 0.5);
        }
        await shot(tester, 'apprentice_report_${tier}_1', settle: 3);
        for (var i = 2; i <= 5; i++) {
          await tester.drag(find.byType(Scrollable).first, const Offset(0, -900));
          await shot(tester, 'apprentice_report_${tier}_$i', settle: 1.5);
        }
      });

      await step(tester, 'gifts_results', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('Spiritual Gifts'));
        await pumpFor(tester, 1.5);
        await shot(tester, 'gifts_sheet', settle: 0.5);
        await tap(tester, find.text('View Latest Results'));
        await shot(tester, 'gifts_results', settle: 5);
      });

      await step(tester, 'apprentice_progress', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('View Progress'));
        await shot(tester, 'apprentice_progress', settle: 5);
      });

      await step(tester, 'apprentice_resources', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('Resources'));
        await shot(tester, 'apprentice_resources', settle: 4);
        await tester.drag(find.byType(Scrollable).first, const Offset(0, -600));
        await shot(tester, 'apprentice_resources_2', settle: 1.5);
      });

      await step(tester, 'prayer_journal', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('Resources'));
        await pumpFor(tester, 2);
        await tap(tester, find.text('Prayer Journal'));
        await shot(tester, 'prayer_journal', settle: 4);
        final add = find.byType(FloatingActionButton);
        if (add.evaluate().isNotEmpty) {
          await tap(tester, add);
          await shot(tester, 'prayer_editor', settle: 2);
        }
      });

      await step(tester, 'apprentice_mentor', ApprenticeDashboardNew, () async {
        await tap(tester, find.byTooltip('Mentor & Agreements'));
        await shot(tester, 'apprentice_mentor', settle: 4);
      });

      await step(tester, 'trivia_home', ApprenticeDashboardNew, () async {
        final tile = find.textContaining('Trivia');
        await tap(tester, tile);
        await shot(tester, 'trivia_home', settle: 4);
      });

      await step(tester, 'apprentice_subscription', ApprenticeDashboardNew, () async {
        await tap(tester, find.byTooltip('My Profile'));
        await shot(tester, 'apprentice_profile', settle: 3);
      });

      await step(tester, 'apprentice_premium', ApprenticeDashboardNew, () async {
        await tap(tester, find.text('New Assessment'));
        await shot(tester, 'choose_assessment_$tier', settle: 3);
        await back(tester);
        Navigator.of(tester.element(find.byType(ApprenticeDashboardNew)))
            .push(MaterialPageRoute(builder: (_) => const SubscriptionScreen()));
        await shot(tester, 'apprentice_subscription_$tier', settle: 4);
      });

      await signOut(tester);

      // ---------- Mentor ----------
      await signIn(tester, mentorEmail, mentorPassword);
      await pumpUntil(tester, find.byType(MentorDashboardNew));
      await pumpFor(tester, 3);
      await clearOverlays(tester);
      await step(tester, 'mentor_dashboard', MentorDashboardNew, () async {
        await shot(tester, 'mentor_dashboard', settle: 5);
      });

      await tap(tester, find.descendant(of: find.byType(BottomNavigationBar), matching: find.text('Apprentices')));
      await pumpFor(tester, 2);

      await step(tester, 'mentor_invite', MentorDashboardNew, () async {
        // The person+ button opens this form (free mentors who already have an apprentice see an upgrade prompt)
        Navigator.of(tester.element(find.byType(MentorDashboardNew)))
            .push(MaterialPageRoute(builder: (_) => ApprenticeInviteScreen(user: FirebaseAuth.instance.currentUser)));
        await shot(tester, 'mentor_invite', settle: 2);
      });

      await step(tester, 'mentor_gifts', MentorDashboardNew, () async {
        await tap(tester, find.byTooltip('Spiritual Gifts'));
        await pumpFor(tester, 3);
        await tap(tester, find.text('Select Apprentice'));
        await pumpFor(tester, 1);
        await tap(tester, find.text('Jordan Davis').last);
        await shot(tester, 'mentor_gifts', settle: 4);
      });

      await step(tester, 'mentor_prayers', MentorDashboardNew, () async {
        await tap(tester, find.byIcon(Icons.more_vert));
        await pumpFor(tester, 1);
        await shot(tester, 'mentor_menu', settle: 0.5);
        await tap(tester, find.text('Prayer Requests'));
        await shot(tester, 'mentor_prayers', settle: 4);
      });

      await step(tester, 'mentor_agreements', MentorDashboardNew, () async {
        await tap(tester, find.byIcon(Icons.more_vert));
        await pumpFor(tester, 1);
        await tap(tester, find.textContaining('Agreement'));
        await shot(tester, 'mentor_agreements', settle: 4);
      });

      await step(tester, 'mentor_assessments', MentorDashboardNew, () async {
        await tap(tester, find.descendant(of: find.byType(BottomNavigationBar), matching: find.text('Assessments')));
        await shot(tester, 'mentor_assessments', settle: 4);
        await tap(tester, find.textContaining('Master').first);
        await pumpFor(tester, 4);
        await tap(tester, find.text('Report'));
        await shot(tester, 'mentor_report_${tier}_1', settle: 8);
        for (var i = 2; i <= 4; i++) {
          await tester.drag(find.byType(Scrollable).last, const Offset(0, -900));
          await shot(tester, 'mentor_report_${tier}_$i', settle: 1.5);
        }
      });

      await step(tester, 'mentor_full_report', MentorDashboardNew, () async {
        await tap(tester, find.descendant(of: find.byType(BottomNavigationBar), matching: find.text('Assessments')));
        await pumpFor(tester, 3);
        await tap(tester, find.textContaining('Master').first);
        await pumpFor(tester, 4);
        await tap(tester, find.text('Report'));
        await pumpFor(tester, 4);
        await tap(tester, find.textContaining('Full Premium Report'));
        for (var i = 0; i < 120 && find.byType(CircularProgressIndicator).evaluate().isNotEmpty; i++) {
          await pumpFor(tester, 0.5);
        }
        await shot(tester, 'mentor_full_report_1', settle: 4);
        for (var i = 2; i <= 5; i++) {
          await tester.drag(find.byType(Scrollable).last, const Offset(0, -900));
          await shot(tester, 'mentor_full_report_$i', settle: 1.5);
        }
      });

      await step(tester, 'mentor_resources', MentorDashboardNew, () async {
        await tap(tester, find.text('Resources').last);
        await shot(tester, 'mentor_resources', settle: 4);
      });

      await step(tester, 'mentor_trivia', MentorDashboardNew, () async {
        await tap(tester, find.text('Trivia').last);
        await shot(tester, 'mentor_trivia', settle: 4);
        await tap(tester, find.text('Apprentices'));
        await pumpFor(tester, 1);
      });

      await step(tester, 'mentor_profile', MentorDashboardNew, () async {
        await tap(tester, find.byTooltip('My Profile'));
        await shot(tester, 'mentor_profile', settle: 3);
      });

      await step(tester, 'mentor_premium', MentorDashboardNew, () async {
        Navigator.of(tester.element(find.byType(MentorDashboardNew)))
            .push(MaterialPageRoute(builder: (_) => const MentorGiftSeatsScreen()));
        await shot(tester, 'mentor_gift_seats', settle: 4);
        await back(tester);
        Navigator.of(tester.element(find.byType(MentorDashboardNew)))
            .push(MaterialPageRoute(builder: (_) => const SubscriptionScreen()));
        await shot(tester, 'mentor_subscription_$tier', settle: 4);
      });

      await signOut(tester);
    }

    FlutterError.onError = testErrorHandler;
    ErrorWidget.builder = testErrorWidgetBuilder;
  });
}
