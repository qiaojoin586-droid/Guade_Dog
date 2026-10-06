/**
 * 常用地址服务：后端 /api/v1/addresses（真实 MySQL 读写）。
 */

import api from './api';

export interface UserAddress {
  id: number;
  label: string;
  address: string;
  lat: number | null;
  lng: number | null;
  is_default: boolean;
  created_at: string;
}

export interface AddressInput {
  label: string;
  address: string;
  lat?: number | null;
  lng?: number | null;
  is_default?: boolean;
}

export async function listAddresses(): Promise<UserAddress[]> {
  const { data } = await api.get('/addresses');
  return (data.data ?? []) as UserAddress[];
}

export async function createAddress(payload: AddressInput): Promise<UserAddress> {
  const { data } = await api.post('/addresses', payload);
  return data.data as UserAddress;
}

export async function updateAddress(id: number, payload: AddressInput): Promise<UserAddress> {
  const { data } = await api.put(`/addresses/${id}`, payload);
  return data.data as UserAddress;
}

export async function deleteAddress(id: number): Promise<void> {
  await api.delete(`/addresses/${id}`);
}
