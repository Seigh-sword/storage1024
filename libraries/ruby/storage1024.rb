# frozen_string_literal: true

require 'net/http'
require 'uri'
require 'json'
require 'securerandom'

# Ruby client for the Storage1024 REST API.
class Storage1024
  def initialize(api_base = nil)
    @api_base = (api_base || ENV['STORAGE1024_API'] || 'https://storage1024.onrender.com/api').sub(%r{/+\z}, '')
    @token = nil
    @user_id = nil
  end

  def set_api_base(url)
    @api_base = url.sub(%r{/+\z}, '')
  end

  def set_token(token)
    @token = token
  end

  def set_user_id(id)
    @user_id = id.to_s
  end

  def set_token_and_id(token, id)
    set_token(token)
    set_user_id(id)
  end

  def get_gv(name)
    data = request(Net::HTTP::Get, project_url("/gv/#{escape(name)}"))
    data['value']
  end

  def gv_json
    request(Net::HTTP::Get, project_url('/gv'))
  end

  def add_gv(name, value)
    request(Net::HTTP::Post, project_url('/gv'), json: { alias: name, value: value.to_s })
  end

  def delete_gv(name)
    request(Net::HTTP::Delete, project_url("/gv/#{escape(name)}"))
  end

  def list_files
    request(Net::HTTP::Get, project_url('/files'))['files'] || {}
  end

  def get_file(alias_name)
    uri = URI.parse(project_url("/files/#{escape(alias_name)}"))
    req = Net::HTTP::Get.new(uri)
    req['Authorization'] = "Bearer #{@token}"
    response = perform(uri, req)
    response.body
  end

  def upload_file(alias_name, file_path)
    boundary = "----Storage1024#{SecureRandom.hex(12)}"
    file_name = File.basename(file_path)
    body = String.new(encoding: Encoding::BINARY)
    body << "--#{boundary}\r\n"
    body << "Content-Disposition: form-data; name=\"alias\"\r\n\r\n#{alias_name}\r\n"
    body << "--#{boundary}\r\n"
    body << "Content-Disposition: form-data; name=\"file\"; filename=\"#{file_name}\"\r\n"
    body << "Content-Type: application/octet-stream\r\n\r\n"
    body << File.binread(file_path)
    body << "\r\n--#{boundary}--\r\n"

    uri = URI.parse(project_url('/upload'))
    req = Net::HTTP::Post.new(uri)
    req['Authorization'] = "Bearer #{@token}"
    req['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
    req.body = body
    JSON.parse(perform(uri, req).body)
  end

  private

  def escape(value)
    URI.encode_www_form_component(value.to_s).gsub('+', '%20')
  end

  def project_url(suffix)
    "#{@api_base}/projects/#{escape(@user_id)}#{suffix}"
  end

  def request(klass, url, json: nil)
    uri = URI.parse(url)
    req = klass.new(uri)
    req['Authorization'] = "Bearer #{@token}"
    if json
      req['Content-Type'] = 'application/json'
      req.body = json.to_json
    end
    JSON.parse(perform(uri, req).body)
  end

  def perform(uri, req)
    # The old client forced use_ssl: true, breaking http:// localhost servers.
    response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: uri.scheme == 'https') do |http|
      http.request(req)
    end
    unless response.is_a?(Net::HTTPSuccess)
      raise "Storage1024 #{response.code}: #{response.body}"
    end
    response
  end
end
