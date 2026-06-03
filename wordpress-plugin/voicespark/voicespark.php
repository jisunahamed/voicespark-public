<?php
/**
 * Plugin Name: VoiceSpark
 * Description: Lets VoiceSpark publish posts and upload media through the WordPress REST API.
 * Version: 1.0.0
 * Author: VoiceSpark
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

const VOICESPARK_TOKEN_PREFIX = 'voicespark_token_';
const VOICESPARK_TOKEN_TTL = 12 * HOUR_IN_SECONDS;

function voicespark_token_key($token) {
    return VOICESPARK_TOKEN_PREFIX . hash('sha256', (string) $token);
}

function voicespark_get_bearer_token() {
    $header = '';
    if (!empty($_SERVER['HTTP_X_VOICESPARK_AUTH'])) {
        $header = sanitize_text_field(wp_unslash($_SERVER['HTTP_X_VOICESPARK_AUTH']));
    } elseif (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
        $header = sanitize_text_field(wp_unslash($_SERVER['HTTP_AUTHORIZATION']));
    } elseif (function_exists('apache_request_headers')) {
        $headers = apache_request_headers();
        if (!empty($headers['Authorization'])) {
            $header = sanitize_text_field($headers['Authorization']);
        }
    }

    if (stripos($header, 'Bearer ') === 0) {
        return trim(substr($header, 7));
    }
    return trim($header);
}

function voicespark_authenticate_request($user_id) {
    if ($user_id) {
        return $user_id;
    }

    $token = voicespark_get_bearer_token();
    if (!$token) {
        return $user_id;
    }

    $stored_user_id = get_transient(voicespark_token_key($token));
    if (!$stored_user_id) {
        return $user_id;
    }

    $user = get_user_by('id', (int) $stored_user_id);
    if (!$user || !user_can($user, 'edit_posts')) {
        return $user_id;
    }

    return (int) $stored_user_id;
}
add_filter('determine_current_user', 'voicespark_authenticate_request', 20);

function voicespark_issue_token(WP_REST_Request $request) {
    $username = sanitize_user((string) $request->get_param('username'));
    $password = (string) $request->get_param('password');

    if (!$username || !$password) {
        return new WP_Error('voicespark_missing_credentials', 'Username and password are required.', array('status' => 400));
    }

    $user = wp_authenticate($username, $password);
    if (is_wp_error($user)) {
        return new WP_Error('voicespark_invalid_credentials', 'Invalid WordPress credentials.', array('status' => 401));
    }

    if (!user_can($user, 'edit_posts') || !user_can($user, 'upload_files')) {
        return new WP_Error('voicespark_insufficient_permissions', 'This user must be able to edit posts and upload media.', array('status' => 403));
    }

    $token = wp_generate_password(64, false, false);
    set_transient(voicespark_token_key($token), (int) $user->ID, VOICESPARK_TOKEN_TTL);

    return rest_ensure_response(array(
        'token' => $token,
        'expires_in' => VOICESPARK_TOKEN_TTL,
        'user_id' => (int) $user->ID,
    ));
}

function voicespark_register_routes() {
    register_rest_route('voicespark/v1', '/token', array(
        'methods' => WP_REST_Server::CREATABLE,
        'callback' => 'voicespark_issue_token',
        'permission_callback' => '__return_true',
    ));
}
add_action('rest_api_init', 'voicespark_register_routes');

