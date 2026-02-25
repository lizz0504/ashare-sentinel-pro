/**
 * API Utilities
 * 统一的API调用工具函数
 */

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

class ApiClient {
  private baseUrl: string;
  private defaultHeaders: HeadersInit;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * 通用GET请求
   */
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'GET',
        headers: this.defaultHeaders,
        credentials: 'include', // 包含认证信息
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      return { success: true, data };
    } catch (error) {
      console.error(`GET request failed for ${endpoint}:`, error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  }

  /**
   * 通用POST请求
   */
  async post<T, R = T>(endpoint: string, data: T): Promise<ApiResponse<R>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers: this.defaultHeaders,
        body: JSON.stringify(data),
        credentials: 'include', // 包含认证信息
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `HTTP error! status: ${response.status}`);
      }

      return { success: true, data: result };
    } catch (error) {
      console.error(`POST request failed for ${endpoint}:`, error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  }

  /**
   * 通用PUT请求
   */
  async put<T, R = T>(endpoint: string, data: T): Promise<ApiResponse<R>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'PUT',
        headers: this.defaultHeaders,
        body: JSON.stringify(data),
        credentials: 'include',
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `HTTP error! status: ${response.status}`);
      }

      return { success: true, data: result };
    } catch (error) {
      console.error(`PUT request failed for ${endpoint}:`, error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  }

  /**
   * 通用DELETE请求
   */
  async delete(endpoint: string): Promise<ApiResponse<void>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'DELETE',
        headers: this.defaultHeaders,
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return { success: true, message: 'Deleted successfully' };
    } catch (error) {
      console.error(`DELETE request failed for ${endpoint}:`, error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  }
}

// 创建全局API客户端实例
const apiClient = new ApiClient();

export { apiClient, ApiClient };
export type { ApiResponse };