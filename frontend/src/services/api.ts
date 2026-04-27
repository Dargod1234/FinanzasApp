import type {
  AuthResponse,
  DashboardSummary,
  EncryptedTransactionPayload,
  EncryptedTransactionRecord,
  PaginatedResponse,
  Profile,
  Transaction,
  TransactionDetail,
} from '../types';
import { getToken, setTokens, clearTokens } from '../utils/storage';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await getToken('access');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    // Merge caller headers
    if (options.headers) {
      const callerHeaders = options.headers as Record<string, string>;
      Object.assign(headers, callerHeaders);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle token refresh on 401
    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        const newToken = await getToken('access');
        headers['Authorization'] = `Bearer ${newToken}`;
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers,
        });
        if (!retryResponse.ok) {
          const errorData = await retryResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || `API Error: ${retryResponse.status}`);
        }
        return retryResponse.json();
      } else {
        await clearTokens();
        window.location.href = '/';
        throw new Error('Session expired');
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  private async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = await getToken('refresh');
      if (!refreshToken) return false;

      const response = await fetch(`${this.baseUrl}/api/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      await setTokens(data.access, data.refresh);
      return true;
    } catch {
      return false;
    }
  }

  // === Auth ===
  async requestOtp(phone_number: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>('/api/auth/phone/request-otp/', {
      method: 'POST',
      body: JSON.stringify({ phone_number }),
    });
  }

  async phoneAuth(phone_number: string, otp_code: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/phone/', {
      method: 'POST',
      body: JSON.stringify({ phone_number, otp_code }),
    });
  }

  // === Profile ===
  async getProfile(): Promise<Profile> {
    return this.request<Profile>('/api/auth/profile/');
  }

  async updateProfile(data: Partial<Profile>): Promise<Profile> {
    return this.request<Profile>('/api/auth/profile/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // === Dashboard ===
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.request<DashboardSummary>('/api/dashboard/summary/');
  }

  // === Transactions ===
  async getTransactions(page = 1, tipo?: string): Promise<PaginatedResponse<Transaction>> {
    const params = new URLSearchParams({ page: String(page) });
    if (tipo) params.set('tipo', tipo);
    return this.request<PaginatedResponse<Transaction>>(
      `/api/transactions/?${params.toString()}`
    );
  }

  async getTransaction(id: number): Promise<TransactionDetail> {
    return this.request<TransactionDetail>(`/api/transactions/${id}/`);
  }

  async updateTransaction(id: number, data: Partial<Transaction>): Promise<Transaction> {
    return this.request<Transaction>(`/api/transactions/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteTransaction(id: number): Promise<void> {
    await fetch(`${this.baseUrl}/api/transactions/${id}/`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${await getToken('access')}`,
      },
    });
  }

  async listEncryptedTransactions(
    page = 1
  ): Promise<PaginatedResponse<EncryptedTransactionRecord>> {
    const params = new URLSearchParams({ page: String(page) });
    return this.request<PaginatedResponse<EncryptedTransactionRecord>>(
      `/api/encrypted-transactions/?${params.toString()}`
    );
  }

  async createEncryptedTransaction(
    payload: EncryptedTransactionPayload
  ): Promise<EncryptedTransactionRecord> {
    return this.request<EncryptedTransactionRecord>('/api/encrypted-transactions/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient(API_BASE);
