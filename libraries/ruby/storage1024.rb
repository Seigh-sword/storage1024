require 'net/http'
require 'uri'
require 'json'

class Storage1024
  def initialize
    @api_base = "https://storage1024.onrender.com/api"
    @token = nil
    @user_id = nil
  end

  def set_token(t)
    @token = t
  end

  def set_user_id(id)
    @user_id = id
  end

  def get_gv(name)
    uri = URI.parse("#{@api_base}/projects/#{@user_id}/gv/#{name}")
    request = Net::HTTP::Get.new(uri)
    request["Authorization"] = "Bearer #{@token}"

    response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) do |http|
      http.request(request)
    end
    response.body
  end

  def add_gv(name, value)
    uri = URI.parse("#{@api_base}/projects/#{@user_id}/gv")
    request = Net::HTTP::Post.new(uri)
    request["Authorization"] = "Bearer #{@token}"
    request["Content-Type"] = "application/json"
    request.body = { alias: name, value: value }.to_json

    response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) do |http|
      http.request(request)
    end
    response.body
  end
end
