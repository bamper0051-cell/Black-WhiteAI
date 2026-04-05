import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';

/// Service for monitoring network connectivity status
class ConnectivityService {
  final Connectivity _connectivity = Connectivity();
  StreamController<bool> connectionChangeController = StreamController<bool>.broadcast();

  ConnectivityService() {
    _initialize();
  }

  void _initialize() {
    _connectivity.onConnectivityChanged.listen((List<ConnectivityResult> results) {
      _checkConnection(results);
    });
  }

  Stream<bool> get connectionChange => connectionChangeController.stream;

  Future<bool> checkConnection() async {
    var connectivityResults = await _connectivity.checkConnectivity();
    return _checkConnection(connectivityResults);
  }

  bool _checkConnection(List<ConnectivityResult> results) {
    bool isConnected = results.any((result) =>
        result == ConnectivityResult.mobile ||
        result == ConnectivityResult.wifi ||
        result == ConnectivityResult.ethernet);

    connectionChangeController.add(isConnected);
    return isConnected;
  }

  void dispose() {
    connectionChangeController.close();
  }
}
